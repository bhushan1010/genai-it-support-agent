"""Request-scoped rulebook priority, then analyzed public-source fallback."""
from __future__ import annotations
import hashlib
from app.core.config import settings
from app.rag.generator import ExtractiveProvider
from app.rag.local_support import SectionRetriever, sections_from_text
from app.rag.web_sources import TrustedWebSearch
from app.workflow.graph import build_graph
from app.workflow.nodes import contextual_query


def run_sections(sections, provider, state):
    mode='semantic' if provider is not None else 'keyword'
    retriever=SectionRetriever(None,mode,provider,top_k=3,
                               score_threshold=settings.retrieval_score_threshold,sections=sections)
    return build_graph(retriever,ExtractiveProvider(sections=sections)).invoke(state)


def resolve_knowledge(body, app_state, state):
    provider=getattr(app_state,'embedding_provider',None)
    notes=[]
    origin='uploaded_rulebook' if body.rulebooks else 'sample_runbook'
    if body.rulebooks:
        sections=[]
        for book in body.rulebooks:
            doc_id='USER-'+hashlib.sha256((book.name+book.content).encode()).hexdigest()[:16].upper()
            sections.extend(sections_from_text(book.content,book.name,doc_id))
        if len(sections)>200:
            raise ValueError('Rulebooks contain too many sections (maximum 200).')
        result=run_sections(sections,provider,state) if sections else {}
        notes.append('Searched only the rulebooks uploaded for this session, before considering internet sources.')
    else:
        result=app_state.graph.invoke(state) if getattr(app_state, "graph", None) is not None else {}
        notes.append('Searched the built-in sample runbooks first.')
    # Matching local policies remain authoritative even without a runnable procedure.
    supported = bool(result.get('evidence_sufficient'))
    if supported and not result.get('steps') and not state.get('attempts') and not result.get('resolved'):
        chunks = result.get('retrieved_chunks', [])
        if chunks:
            from app.rag.context_builder import format_sources
            result['answer'] = "Relevant rulebook guidance was found, but no supported numbered procedure is documented for this request. Follow the rulebook and ask your helpdesk for the next action.\n\n" + "\n\n".join(c.text for c in chunks[:2])
            result['sources'] = format_sources(chunks[:2])
            result['needs_clarification'] = True
    if result.get('error'):
        notes.append('Local retrieval failed; internet advice was not substituted for an unchecked rulebook.')
        result['knowledge_origin'] = origin
        result['analysis'] = notes
        return result
    if supported or not body.internet_fallback:
        result['knowledge_origin']=origin
        result['analysis']=notes
        return result
    notes.append('No applicable local procedure met the evidence checks. Searching official internet documentation.')
    try:
        web_sections,web_notes=TrustedWebSearch().search(state.get('issue_query') or contextual_query(state))
        notes.extend(web_notes)
        if web_sections:
            web_result=run_sections(web_sections,provider,state)
            if web_result.get('evidence_sufficient') and web_result.get('steps'):
                notes.append('Selected a complete numbered procedure after local relevance scoring. Applicability still requires human review.')
                web_result['knowledge_origin']='internet'
                web_result['analysis']=notes
                return web_result
    except Exception:
        notes.append('Internet lookup was unavailable; no public-source resolution was inferred.')
    result.update(answer='No supported resolution was found in the selected rulebooks or the official internet sources checked. Please provide the exact product/version and error, or contact the helpdesk.',
                  steps=[],sources=[],evidence_sufficient=False,needs_clarification=True,needs_escalation=True,
                  knowledge_origin='none',analysis=notes)
    return result
