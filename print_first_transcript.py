import json
from pathlib import Path
from kiwipiepy import Kiwi
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Assumes this script is saved in your repository root.
transcripts_dir = Path(__file__).resolve().parent / "dist" / "transcripts_json"

print(f"Looking in: {transcripts_dir}", flush=True)

files = sorted(transcripts_dir.glob("*.json"))
print(f"JSON files found: {len(files)}", flush=True)


if not files:
    raise FileNotFoundError("No .json files found.")

path = files[7]
print(f"Loading: {path.name}", flush=True)

data = json.loads(path.read_text(encoding="utf-8"))
utterances = data["utterances"]
print(f"Utterances found: {len(utterances)}", flush=True)

text="주무세요"
kiwi = Kiwi()
rules = {
    "계세요": [("계시", "VV", 0,2), ("세요", "EF", 1, 3)],
    "드세요": [("드시", "VV", 0,2), ("세요", "EF",1, 3)],
    "주무세요": [("주무시", "VV", 0,3), ("세요", "EF",2, 4)],
    "잡수세요": [("잡수시", "VV", 0,2), ("세요", "EF",2,4)],
}   

for form, analyzed in rules.items():
    kiwi.add_pre_analyzed_word(form, analyzed, score=100)

print("Kiwi initialized.", flush=True)

print(kiwi.tokenize(text, normalize_coda=True))
'''
tag_names = {
 # --- 체언 (Nominals) ---
    'NNG': '일반 명사 (Common Noun)',
    'NNP': '고유 명사 (Proper Noun)',
    'NNB': '의존 명사 (Bound Noun)',
    'NP':  '대명사 (Pronoun)',
    'NR':  '수사 (Numeral)',
    
    # --- 용언 (Predicates) ---
    'VV':  '동사 (Verb)',
    'VA':  '형용사 (Adjective)',
    'VX':  '보조 용언 (Auxiliary Predicate)',
    'VCP': '긍정 지정사 (Positive Copula - 이다)',
    'VCN': '부정 지정사 (Negative Copula - 아니다)',
    
    # --- 수식언 (Modifiers) ---
    'MM':  '관형사 (Determiner/Adnoun)',
    'MAG': '일반 부사 (General Adverb)',
    'MAJ': '접속 부사 (Conjunctive Adverb)',
    
    # --- 독립언 (Independent) ---
    'IC':  '감탄사 (Interjection)',
    
    # --- 관계언 / 조사 (Particles) ---
    'JKS': '주격 조사 (Subject Case Particle)',
    'JKC': '보격 조사 (Complement Case Particle)',
    'JKG': '관형격 조사 (Adnominal Case Particle)',
    'JKO': '목적격 조사 (Object Case Particle)',
    'JKB': '부사격 조사 (Adverbial Case Particle)',
    'JKV': '호격 조사 (Vocative Case Particle)',
    'JKQ': '인용격 조사 (Quotative Case Particle)',
    'JX':  '보조사 (Auxiliary Particle)',
    'JC':  '접속 조사 (Conjunctive Particle)',
    
    # --- 어미 (Endings) ---
    'EP':  '선어말 어미 (Pre-final Ending)',
    'EF':  '종결 어미 (Final Ending)',
    'EC':  '연결 어미 (Conjunctive Ending)',
    'ETN': '명사형 어미 (Nominalizing Ending)',
    'ETM': '관형사형 어미 (Adnominalizing Ending)',
    
    # --- 접두사 / 접미사 (Affixes) ---
    'XPN': '체언 접두사 (Noun Prefix)',
    'XSN': '명사 파생 접미사 (Noun Derivational Suffix)',
    'XSV': '동사 파생 접미사 (Verb Derivational Suffix)',
    'XSA': '형용사 파생 접미사 (Adjective Derivational Suffix)',
    'XSM': '부사 파생 접미사 (Adverb Derivational Suffix)',
    
    # --- 어근 (Root) ---
    'XR':  '어근 (Root Morpheme)',
    
    # --- 부호 & 기호 (Punctuation & Symbols) ---
    'SF':  '마침표/물음표/느낌표 (Sentence-final Punctuation)',
    'SP':  '쉼표/가운뎃점/콜론 (Separator Punctuation)',
    'SS':  '따옴표/괄호 (Quotation/Bracket)',
    'SE':  '줄임표 (Ellipsis)',
    'SO':  '붙임표/물결표 (Hyphen/Dash)',
    'SW':  '기타 특수 문자/이모티콘 (Other Symbols/Emojis)',
    
    # --- 외국어 & 한자 & 숫자 (Foreign, Character, Numbers) ---
    'SL':  '외국어/알파벳 (Foreign Word/Alphabet)',
    'SH':  '한자 (Chinese Character)',
    'SN':  '숫자 (Number)',
    
    # --- 특수 및 분석 불가 (Special Kiwi Extensions & Unknowns) ---
    'W_URL':  'URL/이메일 주소 (Web URL/Email)',
    'W_MENTION': 'SNS 멘션/@태그 (Social Media Mention)',
    'W_HASHTAG': 'SNS 해시태그/#태그 (Social Media Hashtag)',
    'Z_CODA': '구어체 덧붙은 받침 (Slang Tail Consonant)', 
    'NF':  '명사 추정 범주 (Presumed Noun)',
    'NV':  '용언 추정 범주 (Presumed Predicate)',
    'NA':  '분석 불가능 단어 (Unknown/Unanalyzable Word)'
}

for i, utterance in enumerate(utterances, start=1):
    start, end, text = utterance

    print(f"\n[{i}] {start:.2f}s–{end:.2f}s: {text}")
    for token in kiwi.tokenize(text, normalize_coda=True):
        readable_tag = tag_names.get(token.tag, token.tag)
        print(f"  {token.form:<12} {readable_tag:<5} start={token.start} len={token.len}")

print("\nAnalysis complete.")
'''