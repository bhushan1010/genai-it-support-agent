"""Headless Streamlit checks for session outcome controls and reset."""
import httpx
from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_ui_tracks_outcome_continues_and_resets(monkeypatch):
    posted=[]
    monkeypatch.setattr(httpx,'get',lambda *a,**k:httpx.Response(200,json={'status':'ok','vector_store_docs':41,'llm_provider':'extractive','mock_mode':False}))
    def post(*args,**kwargs):
        posted.append(kwargs['json'])
        index=len(posted)
        return httpx.Response(200,json={
            'answer':'[RUNBOOK EXTRACT] Check the supported section.', 'category':'Network',
            'evidence_sufficient':True,'mock_mode':False,'sources':[],
            'steps':[{'step_id':str(index)*20,'title':f'Section {index}','text':'Check adapter','doc_id':'KB-NET-001', 'prerequisites':[{'text':'Confirm internet access.','doc_id':'KB-NET-001','source_section':'Overview','source_quote':'Internet access'}]}]})
    monkeypatch.setattr(httpx,'post',post)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app/ui/streamlit_app.py'), default_timeout=15).run()
    assert not app.exception
    app.chat_input[0].set_value('My Wi-Fi fails').run()
    assert not app.exception
    assert any('Before you start' in m.value for m in app.markdown)
    assert any('Confirm internet access.' in m.value for m in app.markdown)
    app.selectbox[0].select("Didn't work").run()
    next_button=next(b for b in app.button if b.label=='Show next supported step')
    next_button.click().run()
    assert not app.exception
    assert posted[-1]['attempts']==[{'step_id':'1'*20,'outcome':'did_not_work'}]
    assert posted[-1]['issue_query']=='My Wi-Fi fails'
    assert len(app.selectbox)==2
    app.selectbox[1].select('Worked').run()
    assert app.session_state['resolved']
    next(b for b in app.button if b.label=='New issue / clear session').click().run()
    assert not app.exception
    assert app.session_state['attempts']=={}
    assert app.session_state['messages']==[]
    assert app.session_state['issue_query'] is None


def test_pasted_rulebook_is_sent_and_changing_it_resets_issue(monkeypatch):
    posted=[]
    monkeypatch.setattr(httpx,'get',lambda *a,**k:httpx.Response(200,json={'status':'ok','llm_provider':'extractive'}))
    def post(*args,**kwargs):
        posted.append(kwargs['json'])
        return httpx.Response(200,json={'answer':'Runbook guidance','steps':[],'sources':[],'knowledge_origin':'uploaded_rulebook','answer_mode':'extractive'})
    monkeypatch.setattr(httpx,'post',post)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app/ui/streamlit_app.py'),default_timeout=15).run()
    text='## Step 1 - Printer check\n1. Check printer paper.'
    app.text_area[0].set_value(text).run()
    app.chat_input[0].set_value('Printer paper check').run()
    assert not app.exception
    assert posted[-1]['rulebooks']==[{'name':'pasted-rulebook.md','content':text}]
    assert posted[-1]['internet_fallback'] is True
    app.text_area[0].set_value(text+'\n2. Close the tray.').run()
    assert app.session_state['messages']==[]
    assert app.session_state['issue_query'] is None
