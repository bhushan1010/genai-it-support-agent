"""Bounded, free Microsoft Learn search and analysis of fetched documentation.

No arbitrary URL fetches, snippets-as-evidence, browser execution, or paid calls.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from app.rag.local_support import Section, tokens
from app.rag.retriever import RetrievedChunk

MAX_BYTES = 1_000_000


def allowed_url(url):
    try:
        parsed=urlsplit(url)
        return (parsed.scheme=='https' and parsed.hostname=='learn.microsoft.com'
                and parsed.port in {None,443} and not parsed.username and not parsed.password
                and parsed.path.startswith('/en-us/') and '/answers/' not in parsed.path)
    except ValueError:
        return False


def public_query(query):
    # Only search text is transmitted. Uploaded documents/history are never sent.
    query=re.sub(r'https?://\S+|[\w.+-]+@[\w.-]+|\b(?:\d{1,3}\.){3}\d{1,3}\b', ' ', query)
    query=re.sub(r'(?i)(password|token|secret|api[_ -]?key)\s*[:=]\s*\S+', ' ', query)
    return ' '.join(query.split())[:240]


def read_bounded(client,url,params=None):
    with client.stream('GET',url,params=params,follow_redirects=False) as response:
        if response.is_redirect:
            raise ValueError('Redirected sources are not accepted')
        response.raise_for_status()
        data=bytearray()
        for block in response.iter_bytes():
            data.extend(block)
            if len(data)>MAX_BYTES:
                raise ValueError('Source exceeds download limit')
        return bytes(data)


def parse_document(html, url, query):
    if not allowed_url(url):
        return []
    soup=BeautifulSoup(html,'html.parser')
    candidates=soup.select('main div.content')
    article=max(candidates,key=lambda node:len(node.get_text())) if candidates else soup.select_one('main article') or soup.find('main')
    if not article:
        return []
    for unwanted in article.select('script,style,nav,footer,form,button,aside'):
        unwanted.decompose()
    heading=soup.find('h1')
    page_title=soup.title.get_text(' ',strip=True) if soup.title else heading.get_text(' ',strip=True) if heading else 'Microsoft documentation'
    doc_id='WEB-'+hashlib.sha256(url.encode()).hexdigest()[:12].upper()
    fetched=datetime.now(timezone.utc).isoformat()
    groups=[]
    title=page_title
    content=[]
    has_procedure=False
    for element in article.find_all(['h2','h3','p','ol','ul','pre']):
        if element.find_parent(['ol','ul','pre']):
            continue
        if element.name=='h2':
            if content:
                groups.append((title,content,has_procedure))
            title=element.get_text(' ',strip=True)
            content=[]
            has_procedure=bool(re.match(r"^\d+[.)]\s", title))
        elif element.name=='h3':
            content.append("### " + element.get_text(" ",strip=True))
        elif element.name=='ol':
            items=element.find_all('li',recursive=False)
            if items:
                has_procedure=True
                content.extend(f"{index}. {item.get_text(' ',strip=True)}" for index,item in enumerate(items,start=1))
        elif element.name=='ul':
            content.extend('- '+item.get_text(' ',strip=True) for item in element.find_all('li',recursive=False))
        elif element.name=='pre':
            content.append('```\n'+element.get_text().strip()+'\n```')
        else:
            text=element.get_text(' ',strip=True)
            if text:
                content.append(text)
    if content:
        groups.append((title,content,has_procedure))
    sections=[]
    for index,(title,parts,action) in enumerate(groups):
        text=f'## {title}\n\n'+'\n\n'.join(parts)
        # Reject vague references and incomplete/truncated procedures.
        if not action or len(text)>12000 or len(text)<40:
            continue
        overlap=tokens(query) & tokens(page_title+' '+text)
        if len(overlap)<2:
            continue
        numbered=re.match(r"^(\d+)[.)]\s+(.+)",title)
        if numbered:
            title=f"Step {numbered.group(1)} — {numbered.group(2)}"
            text=f"## {title}\n\n"+'\n\n'.join(parts)
        chunk=RetrievedChunk(text,page_title,doc_id,index,0.0,url,fetched)
        sections.append(Section(chunk,title,index,True))
    return sections


class TrustedWebSearch:
    def search(self, query):
        query=public_query(query)
        if len(tokens(query))<2:
            return [], ['Internet search skipped: provide the affected product and exact symptom.']
        notes=['Uploaded rulebook text was not sent to internet sources.']
        sections=[]
        with httpx.Client(timeout=httpx.Timeout(8.0),headers={'User-Agent':'ITSupportRunbookDemo/1.0'},trust_env=False) as client:
            import json
            data=json.loads(read_bounded(client,'https://learn.microsoft.com/api/search',
                {'search':query,'locale':'en-us','$top':20,'$filter':"category eq 'Documentation'"}))
            candidates=[]
            results=sorted(data.get('results',[]),key=lambda item:len(tokens(query) & tokens(item.get('title',''))),reverse=True)
            for result in results:
                url=result.get('url','')
                if allowed_url(url) and url not in candidates:
                    candidates.append(url)
            for url in candidates[:3]:
                try:
                    raw=read_bounded(client,url)
                    sections.extend(parse_document(raw,url,query))
                except (httpx.HTTPError,ValueError):
                    notes.append('A candidate page could not be fetched or failed the source checks.')
        notes.append(f'Fetched official documentation and found {len(sections)} complete, topic-matching procedure sections.')
        return sections, notes
