"""Rulebook priority, request isolation and analyzed internet fallback."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import httpx
import pytest
from app.api.schemas import SupportRequest, UploadedRulebook
from app.rag.web_sources import allowed_url, parse_document, public_query, read_bounded
from app.rag.local_support import sections_from_text
from app.services.knowledge import resolve_knowledge

BOOK="# Printer guide\n## Prerequisites\n- Have paper available.\n## Step 1 - Orange printer jam\n1. Open the orange printer tray.\n2. Check for a paper jam."
HTML="""<html><head><title>Orange printer repair - Microsoft Learn</title></head><body><main>
<div class="content"><h1>Orange printer repair</h1></div>
<div class="content"><h2>1. Check paper</h2><p>Before repairing the orange printer, check that paper is loaded.</p>
<h2>2. Clear jam</h2><p>Close the orange printer application first.</p><ol><li>Open the tray.</li><li>Remove the jammed paper.</li></ol>
<h3>After checking</h3><p>Close the tray before restarting.</p></div></main></body></html>"""
URL='https://learn.microsoft.com/en-us/windows/orange-printer'


def state(query):
    return {'query':query,'attempts':[],'conversation_history':[]}


def test_uploaded_rulebook_takes_priority_and_never_searches_web(monkeypatch):
    search=MagicMock()
    monkeypatch.setattr('app.services.knowledge.TrustedWebSearch',search)
    body=SupportRequest(query='orange printer jam',rulebooks=[{'name':'printer.md','content':BOOK}],internet_fallback=True)
    app=SimpleNamespace(embedding_provider=None,graph=MagicMock())
    result=resolve_knowledge(body,app,state(body.query))
    assert result['knowledge_origin']=='uploaded_rulebook'
    assert 'orange printer tray' in result['answer']
    assert result['steps'][0]['prerequisites'][0]['text']=='- Have paper available.'
    app.graph.invoke.assert_not_called()
    search.assert_not_called()


def test_missing_rulebook_evidence_runs_analyzed_web_fallback(monkeypatch):
    sections=parse_document(HTML,URL,'orange printer jam')
    search=MagicMock()
    search.return_value.search.return_value=(sections,['Official pages fetched and checked.'])
    monkeypatch.setattr('app.services.knowledge.TrustedWebSearch',search)
    body=SupportRequest(query='orange printer jam',rulebooks=[{'name':'unrelated.txt','content':'Coffee machine descaling instructions.'}],internet_fallback=True)
    result=resolve_knowledge(body,SimpleNamespace(embedding_provider=None),state(body.query))
    assert result['knowledge_origin']=='internet'
    assert result['steps'][0]['position']==1
    assert result['sources'][0]['url']==URL
    assert result['sources'][0]['fetched_at']
    assert 'Official pages fetched and checked.' in result['analysis']
    search.return_value.search.assert_called_once_with(body.query)


def test_failed_web_lookup_does_not_invent_a_resolution(monkeypatch):
    search=MagicMock()
    search.return_value.search.side_effect=httpx.ConnectError('offline')
    monkeypatch.setattr('app.services.knowledge.TrustedWebSearch',search)
    app=SimpleNamespace(embedding_provider=None,graph=MagicMock())
    app.graph.invoke.return_value={'evidence_sufficient':False,'sources':[]}
    body=SupportRequest(query='orange printer jam',internet_fallback=True)
    result=resolve_knowledge(body,app,state(body.query))
    assert result['knowledge_origin']=='none'
    assert result['needs_escalation'] and not result['steps']


def test_internet_disabled_does_not_transmit_query(monkeypatch):
    search=MagicMock()
    monkeypatch.setattr('app.services.knowledge.TrustedWebSearch',search)
    app=SimpleNamespace(embedding_provider=None,graph=MagicMock())
    app.graph.invoke.return_value={'evidence_sufficient':False}
    body=SupportRequest(query='orange printer jam')
    resolve_knowledge(body,app,state(body.query))
    search.assert_not_called()


@pytest.mark.parametrize('url',['http://learn.microsoft.com/en-us/x','https://learn.microsoft.com.evil.test/en-us/x','https://127.0.0.1/en-us/x','https://learn.microsoft.com:8443/en-us/x','https://learn.microsoft.com/en-us/answers/questions/1','https://user@learn.microsoft.com/en-us/x'])
def test_untrusted_urls_are_rejected(url):
    assert not allowed_url(url)


def test_parser_uses_real_article_keeps_numbered_order_and_nested_warnings():
    sections=parse_document(HTML,URL,'orange printer jam')
    assert len(sections)==2
    assert sections[0].title.startswith('Step 1')
    assert sections[1].title.startswith('Step 2')
    assert 'Close the tray before restarting.' in sections[1].chunk.text
    assert all(s.chunk.url==URL for s in sections)
    assert parse_document('<main><p>Just a search snippet.</p></main>',URL,'orange printer jam')==[]


def test_payload_limits_and_empty_rulebooks():
    with pytest.raises(ValueError):
        UploadedRulebook(name='../escape.md',content=BOOK)
    with pytest.raises(ValueError):
        UploadedRulebook(name='empty.md',content='   ')
    with pytest.raises(ValueError):
        SupportRequest(query='printer jam',rulebooks=[{'name':f'{i}.md','content':'x'*80_000} for i in range(3)])


def test_uploaded_content_is_request_scoped():
    body=SupportRequest(query='orange printer jam',rulebooks=[{'name':'printer.md','content':BOOK}])
    app=SimpleNamespace(embedding_provider=None,graph=MagicMock())
    first=resolve_knowledge(body,app,state(body.query))
    app.graph.invoke.return_value={'answer':'No sample evidence','evidence_sufficient':False}
    second=resolve_knowledge(SupportRequest(query=body.query),app,state(body.query))
    assert first['knowledge_origin']=='uploaded_rulebook'
    assert second['answer']=='No sample evidence'


def test_search_query_redacts_common_identifiers():
    query=public_query('printer failure https://internal.test user@corp.test 10.0.0.1 token=secret123')
    assert 'internal.test' not in query and '@' not in query and '10.0.0.1' not in query and 'secret123' not in query


def test_download_limit_and_redirects_are_rejected():
    response=httpx.Response(200,content=b'x'*1_000_001)
    transport=httpx.MockTransport(lambda request: response)
    with httpx.Client(transport=transport) as client:
        with pytest.raises(ValueError):
            read_bounded(client,URL)
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(302,headers={'location':'http://127.0.0.1'}))) as client:
        with pytest.raises(ValueError):
            read_bounded(client,URL)


def test_matching_policy_is_not_overridden_by_public_instructions(monkeypatch):
    search=MagicMock()
    monkeypatch.setattr('app.services.knowledge.TrustedWebSearch',search)
    body=SupportRequest(query='orange printer jam',rulebooks=[{'name':'policy.md','content':'## Orange printer jam policy\nDo not repair the orange printer jam yourself. Contact the internal hardware team.'}],internet_fallback=True)
    result=resolve_knowledge(body,SimpleNamespace(embedding_provider=None),state(body.query))
    assert result['knowledge_origin']=='uploaded_rulebook'
    assert 'Contact the internal hardware team' in result['answer']
    assert not result['steps']
    search.assert_not_called()
