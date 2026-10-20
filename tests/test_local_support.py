"""User-facing free workflow and evaluation invariants."""
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from app.rag.local_support import SectionRetriever, extract_guidance, load_sections
from app.rag.generator import ExtractiveProvider, get_llm_provider
from app.api.schemas import SupportRequest
from app.workflow.graph import build_graph

DOCS = Path('data/sample_docs')

def test_keyword_mode_has_no_model_dependency():
    search = SectionRetriever(DOCS)
    chunks = search.retrieve('VPN client cache')
    assert chunks and chunks[0].doc_id == 'KB-NET-002'
    assert search.provider is None

def test_extractive_guidance_is_full_verbatim_section():
    search = SectionRetriever(DOCS)
    result = extract_guidance(search.retrieve('VPN client cache'), [], search.sections)
    assert result['steps']
    step = result['steps'][0]
    assert any(step['text'] == s.chunk.text for s in search.sections)
    assert 'no generative model' in result['answer']
    assert result['steps'][0]['title'].startswith('Step 1 ')
    assert 'Verify internet connectivity' in result['answer']

def test_attempted_section_is_not_repeated_and_worked_resolves():
    search = SectionRetriever(DOCS)
    chunks = search.retrieve('VPN client cache')
    first = extract_guidance(chunks, [], search.sections)['steps'][0]
    for outcome in ['tried','did_not_work']:
        result = extract_guidance(chunks, [{'step_id':first['step_id'],'outcome':outcome}],search.sections)
        assert all(s['step_id'] != first['step_id'] for s in result['steps'])
    assert extract_guidance(chunks,[{'step_id':first['step_id'],'outcome':'worked'}],search.sections)['resolved']

def test_foreign_attempt_id_does_not_resolve_other_issue():
    search = SectionRetriever(DOCS)
    vpn = extract_guidance(search.retrieve('VPN client cache'), [], search.sections)['steps'][0]
    wifi = extract_guidance(search.retrieve('wireless adapter warning icon'),[{'step_id':vpn['step_id'],'outcome':'worked'}],search.sections)
    assert not wifi['resolved']

def test_exhausted_runbook_escalates():
    search = SectionRetriever(DOCS)
    attempts = [{'step_id':s.step_id,'outcome':'did_not_work'} for s in search.sections if s.chunk.doc_id=='KB-NET-002' and s.action]
    result=extract_guidance(search.retrieve('VPN client cache'),attempts,search.sections)
    assert result['needs_escalation'] and not result['steps']
    assert 'Escalation' in result['answer']

def test_uncovered_question_abstains_without_paid_calls():
    graph=build_graph(SectionRetriever(DOCS),ExtractiveProvider(DOCS))
    result=graph.invoke({'query':'asdfghjkl qwerty 12345'})
    assert result['needs_clarification']
    assert not result['sources']

def test_compiled_graph_tracks_next_step():
    graph=build_graph(SectionRetriever(DOCS),ExtractiveProvider(DOCS))
    first=graph.invoke({'query':'VPN client cache'})
    step=first['steps'][0]
    second=graph.invoke({'query':'Still not working', 'issue_query':'VPN client cache',
                         'attempts':[{'step_id':step['step_id'],'outcome':'did_not_work'}]})
    assert second['steps'][0]['step_id'] != step['step_id']
    assert second['sources'][0]['doc_id']=='KB-NET-002'

def test_dataset_has_60_cases_and_group_isolation():
    cases=json.loads(Path('data/eval/benchmark_v2.json').read_text())['questions']
    assert len(cases)==60
    assert {kind:sum(c['kind']==kind for c in cases) for kind in ['common','followup','partial','out_of_scope']} == {'common':30,'followup':15,'partial':10,'out_of_scope':5}
    tuning={c['family'] for c in cases if c['split']=='calibration'}
    held={c['family'] for c in cases if c['split']=='held_out'}
    assert tuning.isdisjoint(held)
    sections=load_sections(DOCS)
    assert all(not c['evidence_quote'] or any(c['evidence_quote']==s.chunk.text for s in sections) for c in cases)

def test_attempt_payload_is_bounded_and_validated():
    with pytest.raises(ValueError):
        SupportRequest(query='VPN fails', attempts=[{'step_id':'bad','outcome':'worked'}])
    with pytest.raises(ValueError):
        SupportRequest(query='VPN fails', attempts=[{'step_id':'a'*20,'outcome':'unknown'}])

def test_default_free_provider_needs_no_key(monkeypatch):
    from app.core.config import Settings
    settings=Settings(_env_file=None,llm_provider='extractive')
    settings.validate_llm_config()
    assert not settings.requires_api_key()
    assert isinstance(get_llm_provider('extractive'),ExtractiveProvider)


def test_prerequisites_are_source_backed_and_procedure_specific():
    from app.rag.local_support import procedure_prerequisites
    sections=load_sections(DOCS)
    vpn=next(s for s in sections if s.chunk.doc_id=='KB-NET-002' and 'Clear VPN' in s.title)
    checks=procedure_prerequisites(vpn,sections)
    assert any('internet' in c['text'] for c in checks)
    assert any('Disconnect' in c['text'] for c in checks)
    for section in sections:
        if section.action:
            for check in procedure_prerequisites(section,sections):
                if check['source_quote']:
                    assert any(s.chunk.doc_id==check['doc_id'] and s.title==check['source_section'] and check['source_quote'] in ' '.join(s.chunk.text.split()) for s in sections)


def test_admin_prerequisite_and_undocumented_fallback():
    from app.rag.local_support import procedure_prerequisites
    sections=load_sections(DOCS)
    admin=next(s for s in sections if s.chunk.doc_id=='KB-NET-001' and 'TCP/IP' in s.title)
    assert any('administrator' in c['text'] for c in procedure_prerequisites(admin,sections))
    generic=next(s for s in sections if s.chunk.doc_id=='KB-HW-001' and 'current resource' in s.title)
    assert procedure_prerequisites(generic,sections)[0]['source_quote']==''


def test_numbered_runbook_starts_at_one_and_advances_in_order():
    search=SectionRetriever(DOCS)
    chunks=search.retrieve('VPN client cache')
    attempts=[]
    for number in range(1,7):
        result=extract_guidance(chunks,attempts,search.sections)
        step=result['steps'][0]
        assert step['title'].startswith(f'Step {number} ')
        assert step['position']==number
        assert len(step['sequence'])==6
        attempts.append({'step_id':step['step_id'],'outcome':'did_not_work'})
    assert extract_guidance(chunks,attempts,search.sections)['needs_escalation']


def test_alternative_errors_are_not_forced_into_numbered_sequence():
    search=SectionRetriever(DOCS)
    result=extract_guidance(search.retrieve('application license activation'),[],search.sections)
    assert 'License' in result['steps'][0]['title']
    assert result['steps'][0]['sequence']==[]
