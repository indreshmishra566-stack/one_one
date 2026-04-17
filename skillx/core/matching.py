"""
SkillX Smart Matching Engine
----------------------------
Replaces exact string matching with a weighted similarity system:
  - Direct match:   1.0  (python == python)
  - Cluster match:  0.7  (python ≈ django ≈ backend)
  - Tag match:      0.5  (photography ≈ photo editing via shared tag "visual")
  - Partial match:  0.3  (java ≈ javascript via prefix)

A pair is considered a match if the weighted score >= MATCH_THRESHOLD.
"""

from __future__ import annotations
import re
from typing import Dict, List, Tuple


# ── Skill Clusters (semantic neighborhoods) ─────────────────────────────────
SKILL_CLUSTERS: Dict[str, List[str]] = {
    # Programming
    'python_ecosystem':   ['python', 'django', 'flask', 'fastapi', 'numpy', 'pandas', 'pytorch', 'tensorflow', 'ml', 'machine learning', 'data science', 'ai', 'artificial intelligence', 'backend', 'scripting'],
    'javascript_ecosystem': ['javascript', 'js', 'typescript', 'ts', 'react', 'vue', 'angular', 'nextjs', 'nodejs', 'node', 'frontend', 'web dev', 'webdev', 'svelte'],
    'java_ecosystem':     ['java', 'spring', 'kotlin', 'android', 'jvm', 'maven', 'gradle'],
    'systems':            ['c', 'c++', 'cpp', 'rust', 'go', 'golang', 'assembly', 'embedded', 'systems programming', 'os', 'linux', 'kernel'],
    'data':               ['sql', 'mysql', 'postgres', 'postgresql', 'mongodb', 'database', 'db', 'data engineering', 'etl', 'spark', 'hadoop', 'data analysis', 'analytics', 'excel', 'tableau', 'power bi'],
    'devops':             ['devops', 'docker', 'kubernetes', 'k8s', 'aws', 'azure', 'gcp', 'cloud', 'terraform', 'ansible', 'ci/cd', 'github actions', 'jenkins', 'nginx', 'linux', 'bash', 'shell'],
    'mobile':             ['flutter', 'dart', 'swift', 'ios', 'android', 'react native', 'kotlin', 'mobile dev', 'xcode'],
    'security':           ['cybersecurity', 'security', 'hacking', 'ethical hacking', 'pentesting', 'ctf', 'networking', 'cryptography', 'infosec'],
    # Design
    'visual_design':      ['design', 'ui', 'ux', 'ui/ux', 'graphic design', 'figma', 'sketch', 'adobe xd', 'illustrator', 'photoshop', 'canva', 'visual design', 'branding', 'logo design'],
    'photo_video':        ['photography', 'photo editing', 'lightroom', 'photoshop', 'videography', 'video editing', 'premiere', 'after effects', 'davinci resolve', 'cinematography', 'youtube'],
    '3d_art':             ['3d', 'blender', '3ds max', 'maya', 'cinema 4d', 'modeling', '3d modeling', 'animation', '3d animation', 'vfx', 'game design'],
    # Music
    'music_production':   ['music production', 'beatmaking', 'fl studio', 'ableton', 'logic pro', 'garage band', 'mixing', 'mastering', 'audio engineering', 'sound design', 'edm', 'producing'],
    'instruments':        ['guitar', 'piano', 'keyboard', 'drums', 'bass', 'violin', 'ukulele', 'singing', 'vocals', 'music theory', 'songwriting', 'composition'],
    # Business
    'marketing':          ['marketing', 'digital marketing', 'seo', 'sem', 'social media', 'content marketing', 'email marketing', 'growth hacking', 'ads', 'facebook ads', 'google ads', 'copywriting'],
    'entrepreneurship':   ['entrepreneurship', 'startup', 'business', 'product management', 'pm', 'agile', 'scrum', 'leadership', 'strategy', 'consulting'],
    'finance':            ['finance', 'accounting', 'investing', 'trading', 'stocks', 'crypto', 'blockchain', 'defi', 'financial modeling', 'excel', 'budgeting'],
    # Languages
    'spanish':            ['spanish', 'español', 'castilian'],
    'french':             ['french', 'français'],
    'german':             ['german', 'deutsch'],
    'mandarin':           ['mandarin', 'chinese', 'cantonese', 'mandarin chinese'],
    'japanese':           ['japanese', 'nihongo', 'kanji'],
    'arabic':             ['arabic', 'عربي'],
    # Health & Lifestyle
    'fitness':            ['fitness', 'gym', 'weightlifting', 'calisthenics', 'crossfit', 'yoga', 'pilates', 'personal training', 'nutrition', 'diet', 'running', 'cycling'],
    'cooking':            ['cooking', 'baking', 'chef', 'culinary', 'meal prep', 'pastry', 'cuisine', 'recipe', 'food'],
    'games':              ['chess', 'poker', 'gaming', 'game theory', 'esports', 'speedrunning', 'board games'],
    # Content & Writing
    'writing':            ['writing', 'copywriting', 'blogging', 'content writing', 'storytelling', 'creative writing', 'journalism', 'technical writing', 'proofreading', 'editing'],
}

# ── Tag System (cross-cluster groupings) ─────────────────────────────────────
SKILL_TAGS: Dict[str, List[str]] = {
    'creative':    ['design', 'photography', 'videography', 'writing', 'music production', 'illustration', 'animation', 'blender', 'storytelling', 'composing'],
    'technical':   ['python', 'javascript', 'java', 'c++', 'rust', 'sql', 'docker', 'linux', 'networking'],
    'analytical':  ['data science', 'analytics', 'finance', 'accounting', 'statistics', 'math', 'research'],
    'social':      ['marketing', 'sales', 'leadership', 'communication', 'public speaking', 'coaching', 'teaching'],
    'physical':    ['yoga', 'fitness', 'gym', 'dance', 'sports', 'martial arts', 'swimming', 'running'],
    'language':    ['spanish', 'french', 'german', 'mandarin', 'japanese', 'arabic', 'italian', 'portuguese'],
    'business':    ['marketing', 'entrepreneurship', 'finance', 'consulting', 'product management'],
    'music':       ['guitar', 'piano', 'drums', 'singing', 'music production', 'music theory'],
    'visual':      ['photography', 'design', 'video editing', '3d', 'illustration', 'ui', 'ux'],
    'coding':      ['python', 'javascript', 'java', 'c++', 'rust', 'go', 'typescript', 'swift', 'kotlin'],
}

MATCH_THRESHOLD = 0.35   # minimum weighted score to be considered a match
EXACT_WEIGHT    = 1.0
CLUSTER_WEIGHT  = 0.70
TAG_WEIGHT      = 0.45
PARTIAL_WEIGHT  = 0.25


def _normalize(skill: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r'\s+', ' ', skill.strip().lower())


def _parse_skills(raw: str) -> List[str]:
    """Split comma/newline separated string into normalized skill list."""
    parts = re.split(r'[,\n]+', raw)
    return [_normalize(p) for p in parts if p.strip()]


def _build_cluster_map() -> Dict[str, str]:
    """Map each skill → its cluster name."""
    m: Dict[str, str] = {}
    for cluster, skills in SKILL_CLUSTERS.items():
        for s in skills:
            m[_normalize(s)] = cluster
    return m


def _build_tag_map() -> Dict[str, List[str]]:
    """Map each skill → list of tags it belongs to."""
    m: Dict[str, List[str]] = {}
    for tag, skills in SKILL_TAGS.items():
        for s in skills:
            ns = _normalize(s)
            m.setdefault(ns, []).append(tag)
    return m


_CLUSTER_MAP = _build_cluster_map()
_TAG_MAP = _build_tag_map()


def _skill_similarity(a: str, b: str) -> float:
    """Return similarity score between two individual skills."""
    a, b = _normalize(a), _normalize(b)
    if a == b:
        return EXACT_WEIGHT

    # Cluster match
    ca, cb = _CLUSTER_MAP.get(a), _CLUSTER_MAP.get(b)
    if ca and cb and ca == cb:
        return CLUSTER_WEIGHT

    # Tag overlap
    ta = set(_TAG_MAP.get(a, []))
    tb = set(_TAG_MAP.get(b, []))
    shared_tags = ta & tb
    if shared_tags:
        return TAG_WEIGHT

    # Partial string match (one contains the other)
    if len(a) >= 3 and len(b) >= 3 and (a in b or b in a):
        return PARTIAL_WEIGHT

    return 0.0


def skill_match_score(skills_a: List[str], skills_b: List[str]) -> Tuple[float, List[Tuple[str, str, float]]]:
    """
    Given two skill lists, return:
      - total_score: sum of best match scores for each skill in A against B
      - pairs: list of (skill_a, best_matching_skill_b, score) sorted by score desc

    Score is normalized by len(skills_a) so it stays in [0, 1].
    """
    if not skills_a or not skills_b:
        return 0.0, []

    pairs = []
    total = 0.0
    for sa in skills_a:
        best_score = 0.0
        best_sb = ''
        for sb in skills_b:
            s = _skill_similarity(sa, sb)
            if s > best_score:
                best_score = s
                best_sb = sb
        if best_score > 0:
            pairs.append((sa, best_sb, best_score))
            total += best_score

    normalized = total / len(skills_a)
    pairs.sort(key=lambda x: x[2], reverse=True)
    return normalized, pairs


def compute_match(user_have: str, user_want: str,
                  other_have: str, other_want: str) -> Dict:
    """
    Full bidirectional match computation.
    Returns a dict with:
      - is_match: bool
      - score: float (combined weighted score 0-1)
      - i_learn_score, they_learn_score: individual direction scores
      - i_learn_pairs, they_learn_pairs: matched skill pairs
    """
    u_have = _parse_skills(user_have)
    u_want = _parse_skills(user_want)
    o_have = _parse_skills(other_have)
    o_want = _parse_skills(other_want)

    # How well can the other person satisfy what I want?
    i_learn_score, i_learn_pairs = skill_match_score(u_want, o_have)
    # How well can I satisfy what the other person wants?
    they_learn_score, they_learn_pairs = skill_match_score(o_want, u_have)

    # Both directions must exceed threshold for a true match
    combined = (i_learn_score + they_learn_score) / 2
    is_match = i_learn_score >= MATCH_THRESHOLD and they_learn_score >= MATCH_THRESHOLD

    return {
        'is_match': is_match,
        'score': round(combined, 3),
        'i_learn_score': round(i_learn_score, 3),
        'they_learn_score': round(they_learn_score, 3),
        'i_learn_pairs': i_learn_pairs,
        'they_learn_pairs': they_learn_pairs,
    }


def find_best_match_from_queue(current_user_id: int,
                               current_have: str,
                               current_want: str,
                               queue: list) -> Tuple[int | None, float]:
    """
    Given the live queue (list of dicts with user_id, skills_have, skills_want),
    find the best-scoring compatible user.
    Returns (user_id, score) or (None, 0).
    """
    best_id = None
    best_score = 0.0

    for entry in queue:
        if entry['user_id'] == current_user_id:
            continue
        result = compute_match(
            current_have, current_want,
            entry['skills_have'], entry['skills_want']
        )
        if result['is_match'] and result['score'] > best_score:
            best_score = result['score']
            best_id = entry['user_id']

    return best_id, best_score
