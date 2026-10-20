"""Free section-level retrieval and verbatim runbook guidance.

Scores rank evidence; they are not probabilities. No model generates commands.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.loader import _extract_doc_id
from app.rag.retriever import RetrievedChunk

STOP_WORDS = set("a an the my our your i we it is are was were be been to of and or for in on at with from after before do does did not no still have has had can cannot could should what how why when this that please help me work working issue problem get getting about since very then also but as if into try tried".split())
ALIASES = {"wireless": "wifi", "wi": "wifi", "fi": "wifi", "slowly": "slow", "sluggish": "slow", "hot": "thermal", "overheating": "thermal", "signin": "login", "locked": "lockout", "unlock": "lockout", "dlls": "dll", "crashing": "crash", "crashes": "crash", "freezes": "freeze", "errors": "error", "credentials": "password", "certificate": "certificate"}


def tokens(text: str) -> set[str]:
    text = re.sub(r"wi[ -]fi", "wifi", text.lower())
    return {ALIASES.get(t, t) for t in re.findall(r"[a-z0-9]+", text) if t not in STOP_WORDS and len(t) > 1}


@dataclass
class Section:
    chunk: RetrievedChunk
    title: str
    order: int
    action: bool

    @property
    def step_id(self) -> str:
        return hashlib.sha256(f"{self.chunk.doc_id}:{self.title}:{self.chunk.text}".encode()).hexdigest()[:20]


def load_sections(path: Path) -> list[Section]:
    sections = []
    for file in sorted(path.iterdir()):
        if not file.is_file() or file.suffix.lower() not in {".md", ".txt"} or file.name.lower() == "readme.md":
            continue
        if file.stat().st_size > 1_000_000:
            continue
        raw = file.read_text(encoding="utf-8")
        sections.extend(sections_from_text(raw, file.name))
    if not sections:
        raise ValueError(f"No Markdown runbook sections found in {path}")
    return sections


def sections_from_text(raw, filename, doc_id=None):
    doc_id = doc_id or _extract_doc_id(raw, filename)
    if not re.search(r"(?m)^## +", raw):
        raw = "## Procedure\n\n" + raw
    sections = []
    for index, part in enumerate(re.split(r"(?m)^## +", raw)[1:]):
        title, _, body = part.partition("\n")
        body = re.sub(r"(?m)^---\s*$", "", body).strip()
        if body:
            action = title.lower().startswith("step ") or bool(re.search(r"(?m)^\d+\. ", body))
            sections.append(Section(RetrievedChunk(f"## {title}\n\n{body}", filename, doc_id, index, 0.0), title, index, action))
    return sections


class SectionRetriever:
    """Compare keyword, local semantic and weighted hybrid retrieval over identical sections."""
    def __init__(self, docs_path: Path, mode="keyword", embedding_provider=None,
                 top_k=3, score_threshold=0.6, sections=None):
        if mode not in {"keyword", "semantic", "hybrid"}:
            raise ValueError(f"Unsupported retrieval mode: {mode}")
        if mode != "keyword" and embedding_provider is None:
            raise ValueError("Semantic and hybrid modes need local embeddings")
        self.sections = list(sections) if sections is not None else load_sections(docs_path)
        self.mode, self.top_k, self.score_threshold = mode, top_k, score_threshold
        self.provider = embedding_provider
        self.term_sets = [tokens(s.chunk.source + " " + s.title + " " + s.chunk.text) for s in self.sections]
        frequencies = Counter(term for terms in self.term_sets for term in terms)
        self.idf = {t: math.log((len(self.sections) + 1) / (n + 1)) + 1 for t, n in frequencies.items()}
        self.vectors = embedding_provider.embed([s.chunk.source + "\n" + s.chunk.text for s in self.sections]) if embedding_provider else None

    def count(self):
        return len(self.sections)

    def rank(self, query: str) -> list[RetrievedChunk]:
        terms = tokens(query)
        if not terms:
            return []
        weights = {t: self.idf.get(t, math.log(len(self.sections) + 1) + 1) for t in terms}
        total = sum(weights.values())
        qvector = self.provider.embed_query(query) if self.mode != "keyword" else None
        ranked = []
        for index, section in enumerate(self.sections):
            lexical = sum(weights[t] for t in terms & self.term_sets[index]) / total
            keyword_score = 0.5 + lexical / 2 if lexical else 0.0
            if qvector is not None:
                vec = self.vectors[index]
                norm = math.sqrt(sum(v*v for v in vec) * sum(v*v for v in qvector))
                cosine = sum(a*b for a,b in zip(vec, qvector)) / norm if norm else 0.0
                semantic = max(0.0, min(1.0, (1 + cosine) / 2))
            else:
                semantic = 0.0
            score = {"keyword": keyword_score, "semantic": semantic,
                     "hybrid": 0.5 * keyword_score + 0.5 * semantic}[self.mode]
            c = section.chunk
            ranked.append(RetrievedChunk(c.text, c.source, c.doc_id, c.chunk_index, round(score, 6), c.url, c.fetched_at))
        return sorted(ranked, key=lambda c: (-c.score, c.doc_id, c.chunk_index))

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        return [c for c in self.rank(query) if c.score >= self.score_threshold][:self.top_k]


def procedure_prerequisites(section, sections):
    """Source-backed checks displayed beside a procedure, never assumed verified."""
    checks = []
    doc_sections = [s for s in sections if s.chunk.doc_id == section.chunk.doc_id]

    def add(label, quote):
        match = next((s for s in doc_sections if quote in " ".join(s.chunk.text.split())), None)
        if match:
            checks.append({"text": label, "source_quote": quote,
                           "doc_id": match.chunk.doc_id, "source_section": match.title})

    text = " ".join(section.chunk.text.split())
    title = section.title.lower()
    doc = section.chunk.doc_id
    if doc == "KB-NET-002":
        add("Confirm that you have a working internet connection before troubleshooting VPN.",
            "VPN cannot connect without a working internet connection.")
        if "credentials" in title:
            add("Have your corporate username and current password available. Do not share them here.",
                "Use your corporate username (firstname.lastname format) and current password.")
        if "cache" in title:
            add("Disconnect and close the VPN client before clearing its cache.",
                "Disconnect and close the VPN client.")
        if "server address" in title:
            add("Use the server address published by IT; ask IT before changing it.",
                "Do not change the server address without IT confirmation.")
    if doc == "KB-NET-001":
        add("Check whether other devices are affected. If none can connect, report the network issue instead.",
            "If no device can connect: the access point or the broader network may be down.")
        if "reconnect" in title:
            add("Make sure you know the network passphrase, or contact the helpdesk.",
                "If you do not know the passphrase: contact the IT helpdesk.")
    if "administrator" in text.lower():
        add("This procedure includes an administrator action. If you cannot perform it, ask IT for assistance.",
            "Command Prompt as Administrator" if "Command Prompt as Administrator" in text else "Run as administrator")
    if doc == "KB-AUTH-001" and "self-service" in title:
        add("Use self-service reset only if you previously registered for it.",
            "If you have previously registered for self-service reset:")
        add("Have access to one of your registered verification methods.",
            "Choose a verification method: authenticator app, email to your registered personal address, or SMS to your registered phone number.")
    if doc == "KB-AUTH-001" and "helpdesk-assisted" in title:
        add("Be prepared to verify your identity with the helpdesk.",
            "The helpdesk agent will verify your identity using your employee ID and at least one additional factor")
    if doc == "KB-HW-001" and "startup" in title:
        add("Do not disable security software, VPN clients or IT management agents.",
            "Do not disable security software, VPN clients, or IT management agents.")
    if doc == "KB-HW-001" and "disk" in title:
        add("Only remove files you recognize; do not delete system files.",
            "Do not delete system files or files you cannot identify.")
    if doc == "KB-APP-001" and "license" in title:
        add("Use your corporate account and connect to the corporate network or VPN.",
            "Confirm you are connected to the corporate network or VPN.")
    if doc.startswith(("USER-", "WEB-")):
        for prerequisite_section in doc_sections:
            if any(word in prerequisite_section.title.lower() for word in ["prerequisite", "before you", "requirements"]):
                quote = prerequisite_section.chunk.text.split("\n\n", 1)[-1].strip()
                if quote:
                    checks.append({"text": quote, "source_quote": " ".join(quote.split()),
                                   "doc_id": doc, "source_section": prerequisite_section.title})
    if not checks:
        # Avoid inventing environment or access requirements absent from the runbook.
        checks.append({"text": "No separate prerequisites are documented for this section. Check that the symptoms match, and review the procedure before making changes.",
                       "source_quote": "", "doc_id": doc, "source_section": section.title})
    return checks


def extract_guidance(chunks, attempts, sections):
    """Return the next full runbook section; ignore IDs outside the selected document."""
    if not chunks:
        return {"answer": "No supported runbook guidance found. Please describe the affected system and exact error.",
                "steps": [], "resolved": False, "needs_clarification": True, "needs_escalation": False, "sources": []}
    doc_id = chunks[0].doc_id
    actions = [s for s in sections if s.chunk.doc_id == doc_id and s.action]
    outcomes = {a["step_id"]: a["outcome"] for a in attempts}
    if any(outcomes.get(s.step_id) == "worked" for s in actions):
        return {"answer": "You marked a troubleshooting section as worked. This issue is recorded as resolved for this session. Start a new issue to troubleshoot something else.",
                "steps": [], "resolved": True, "needs_clarification": False, "needs_escalation": False, "sources": []}
    numbered = bool(actions) and all(re.match(r"^Step \d+", s.title, re.I) for s in actions)
    if numbered:
        actions = sorted(actions, key=lambda s: s.order)
        pending = [s for s in actions if s.step_id not in outcomes]
    else:
        # Error-specific alternatives (e.g. DLL vs license errors) are not a sequence.
        by_key = {(s.chunk.doc_id, s.chunk.chunk_index): s for s in actions if s.step_id not in outcomes}
        pending = [by_key[(c.doc_id, c.chunk_index)] for c in chunks if (c.doc_id, c.chunk_index) in by_key]
    if not pending:
        escalation = next((s for s in sections if s.chunk.doc_id == doc_id and s.title.lower() == "escalation"), None)
        text = escalation.chunk.text if escalation else "Please contact the IT helpdesk with the exact error and steps already attempted."
        return {"answer": "[RUNBOOK EXTRACT — no generative model]\n\nNo further supported troubleshooting section is available.\n\n" + text,
                "steps": [], "resolved": False, "needs_clarification": True, "needs_escalation": True,
                "sources": [escalation.chunk] if escalation else []}
    section = pending[0]
    return {"answer": "[RUNBOOK EXTRACT — no generative model]\n\n" + section.chunk.text + f"\n\nSource: [{doc_id}]. Mark the outcome below. These steps cover this runbook only; describe any additional symptoms or exact errors before applying guidance to a different issue.",
            "steps": [{"step_id": section.step_id, "title": section.title, "text": section.chunk.text, "doc_id": doc_id,
                       "prerequisites": procedure_prerequisites(section, sections),
                       "sequence": [s.title for s in actions] if numbered else [],
                       "position": actions.index(section) + 1 if numbered else None}],
            "resolved": False, "needs_clarification": False, "needs_escalation": False,
            "sources": [section.chunk]}
