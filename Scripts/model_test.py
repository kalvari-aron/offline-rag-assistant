"""
Day 1 - Model selection test.

Runs the same Hungarian questions against several local Ollama models,
using a short fictional policy excerpt as context (a mini RAG simulation).
Saves answers and speed metrics to results/ as a Markdown file for manual scoring.

Usage:
    pip install ollama
    python scripts/model_test.py
"""

import time
from datetime import datetime
from pathlib import Path

import ollama

# Check the exact model names with:  ollama list
MODELS = ["gemma4:12b", "qwen2.5:14b"]

CONTEXT = """
PÉLDA KFT. - INFORMATIKAI BIZTONSÁGI SZABÁLYZAT (kivonat)

3.1 Jelszavak: A jelszó legalább 12 karakter hosszú, és tartalmaz kis- és nagybetűt,
számot, valamint speciális karaktert. Rendszeres, időszakos jelszócsere nem kötelező;
jelszót csak akkor kell cserélni, ha felmerül a gyanú, hogy illetéktelen személy megismerte.

3.2 Képernyőzár: Felügyelet nélkül hagyott munkaállomás képernyője legkésőbb 5 perc
inaktivitás után automatikusan zárolódik.

3.3 Adathordozók: Saját USB-adathordozó (pendrive, külső merevlemez) használata tilos.
Kizárólag az IT osztály által kiadott, titkosított céges adathordozó használható,
az IT vezető előzetes engedélyével.

4.1 Biztonsági incidens: Gyanús e-mailt, rosszindulatú hivatkozásra kattintást vagy
egyéb biztonsági eseményt az észleléstől számított 1 órán belül jelenteni kell
az it-biztonsag@peldakft.hu címen vagy az 1234-es belső mellék telefonszámon.

5.1 Adatminősítés: A cég négy adatminősítési kategóriát alkalmaz: Nyilvános, Belső,
Bizalmas és Szigorúan bizalmas.

5.2 Bizalmas adatok továbbítása: Bizalmas vagy Szigorúan bizalmas besorolású dokumentum
külső félnek csak titkosított formában, az adatgazda előzetes jóváhagyásával küldhető.

6.1 Távmunka: A céges rendszerek távoli elérése kizárólag a céges VPN-en keresztül,
többfaktoros hitelesítéssel (MFA) engedélyezett.

7.1 Jogosultságkezelés: Új jogosultság igénylését a munkavállaló közvetlen vezetője
kezdeményezi, és az IT vezető hagyja jóvá.
"""

# The last two questions are traps:
#  - Q9 is NOT answered in the context -> the model must say it has no information
#  - Q10 is a leading question with a false premise -> the model must not agree
QUESTIONS = [
    "Legalább hány karakter hosszú legyen a jelszavam?",
    "Mennyi idő után kell automatikusan zárolódnia a képernyőnek?",
    "Használhatom a saját pendrive-omat a céges gépen?",
    "Rákattintottam egy gyanús e-mailben lévő linkre. Mit kell tennem és mennyi időn belül?",
    "Milyen adatminősítési kategóriák vannak a cégnél?",
    "Elküldhetek egy bizalmas dokumentumot e-mailben egy külső partnernek?",
    "Otthonról dolgozom. Hogyan érhetem el a céges rendszereket?",
    "Ki hagyja jóvá, ha új jogosultságra van szükségem?",
    "Hány nap szabadság jár nekem évente?",
    "Ugye félévente kötelező lecserélni a jelszavamat?",
]

SYSTEM_PROMPT = """Te a Példa Kft. belső szabályzat-asszisztense vagy.
Kizárólag az alábbi KONTEXTUS alapján válaszolj, magyarul, tömören.
Ha a válasz nem található a kontextusban, pontosan ezt írd:
"A rendelkezésre álló dokumentumokban erre nincs információ."
Ne találj ki semmit, és ne fogadd el a kérdésben szereplő állítást, ha a kontextus mást mond.

KONTEXTUS:
{context}"""

OPTIONS = {"temperature": 0.1, "num_ctx": 8192}


def chat(model: str, messages: list):
    """Call the model with thinking mode off; retry without the flag if unsupported."""
    try:
        return ollama.chat(model=model, messages=messages, options=OPTIONS, think=False)
    except Exception:
        return ollama.chat(model=model, messages=messages, options=OPTIONS)


def ask(model: str, question: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=CONTEXT)},
        {"role": "user", "content": question},
    ]
    start = time.perf_counter()
    resp = chat(model, messages)
    elapsed = time.perf_counter() - start

    tokens = resp.eval_count or 0
    gen_seconds = (resp.eval_duration or 0) / 1e9
    tokens_per_sec = tokens / gen_seconds if gen_seconds else 0.0
    return resp.message.content.strip(), elapsed, tokens_per_sec


def main():
    results = {m: [] for m in MODELS}

    for model in MODELS:
        print(f"\n=== {model} ===")
        print("Loading model into VRAM (warm-up)...")
        chat(model, [{"role": "user", "content": "Szia!"}])

        for i, q in enumerate(QUESTIONS, start=1):
            answer, elapsed, tps = ask(model, q)
            results[model].append((answer, elapsed, tps))
            print(f"Q{i}: {elapsed:.1f} s, {tps:.0f} tokens/s")

    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_file = out_dir / f"model_test_{stamp}.md"

    lines = [
        f"# Model test - {stamp}",
        "",
        "Scoring: 2 = correct and complete, 1 = partially correct, 0 = wrong or made up.",
        "Q9 is correct only if the model says there is no information.",
        "Q10 is correct only if the model rejects the false premise.",
        "",
    ]
    for i, q in enumerate(QUESTIONS, start=1):
        lines.append(f"## Q{i}: {q}")
        lines.append("")
        for model in MODELS:
            answer, elapsed, tps = results[model][i - 1]
            lines.append(f"**{model}** ({elapsed:.1f} s, {tps:.0f} tokens/s) - Score: _/2")
            lines.append("")
            lines.append(answer)
            lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Model | Score (max 20) | Avg. time (s) | Avg. speed (tokens/s) |")
    lines.append("|-------|----------------|---------------|-----------------------|")
    for model in MODELS:
        avg_time = sum(r[1] for r in results[model]) / len(QUESTIONS)
        avg_tps = sum(r[2] for r in results[model]) / len(QUESTIONS)
        lines.append(f"| {model} | _ | {avg_time:.1f} | {avg_tps:.0f} |")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults saved to: {out_file}")


if __name__ == "__main__":
    main()
