import pandas as pd
import numpy as np
import unicodedata
import spacy
import re


NLP = spacy.load("pt_core_news_sm", disable=["parser", "tagger", "lemmatizer"])

BR_NAMES = {
    "João", "Gabriel", "Lucas", "Pedro", "Mateus", "José", "Gustavo", "Guilherme", "Carlos",
    "Vitor", "Felipe", "Antônio", "Francisco", "Luiz", "Marcos", "Miguel", "Rafael", "Daniel",
    "Bruno", "Leonardo", "Thiago", "Rodrigo", "Fernando", "Eduardo", "Marcelo", "André",
    "Ricardo", "Ronaldo", "Paulo", "Alexandre", "Caio", "Davi", "Vinícius", "Estevão",
    "Joaquim", "Samuel", "Elias", "Raul", "Henrique", "Bernardo", "Diego", "Mário", "Otávio",
    "Sérgio", "Roberto", "Rogério", "Celso", "Fábio", "Ademir", "Adriano", "Afonso", "Aldo",
    "Alex", "Altamiro", "Anderson", "Arnaldo", "Arthur", "Augusto", "Benedito", "Breno",
    "César", "Cláudio", "Cristóvão", "Denis", "Diogo", "Edson", "Emanuel", "Emílio", "Enzo",
    "Erik", "Evandro", "Fabrício", "Flávio", "Frederico", "Geraldo", "Gilberto", "Giovanni",
    "Gonçalo", "Heitor", "Hélio", "Humberto", "Inácio", "Isaac", "Ivo", "Jair", "Javier",
    "Jorge", "Julio", "Júlio", "Luan", "Luís", "Márcio", "Maurício", "Murilo", "Natanael",
    "Neymar", "Nicolau", "Nuno", "Osvaldo", "Pablo", "Patrick", "Pietro", "Ramon", "Renato",
    "Ravi", "Renan", "Rubens", "Salvador", "Santiago", "Sebastião", "Silas", "Silvano",
    "Simão", "Tales", "Theo", "Tobias", "Tomás", "Ubiratã", "Ulisses", "Valdemar", "Vasco",
    "Vicente", "Washington", "Zeca", "Zélio", "Zico", "Ayrton", "Cauã", "Dorian", "Kauã",
    "Lúcio", "Mateo", "Maximiliano", "Pascoal", "Quim", "Raimundo", "Reginaldo", "Rodolfo",
    "Romário", "Silvino", "Tadeu", "Tiburcio", "Tristão", "Valentin", "Vitorino", "Zeferino",
    "Maria", "Ana", "Helena", "Alice", "Laura", "Sophia", "Isabella", "Manuela", "Valentina",
    "Júlia", "Heloísa", "Luísa", "Lorena", "Lívia", "Cecília", "Eloá", "Isadora", "Beatriz",
    "Mariana", "Lara", "Emanuelly", "Melissa", "Carolina", "Gabriela", "Rafaela", "Clara",
    "Sophia", "Vitória", "Yasmin", "Fernanda", "Camila", "Giovanna", "Larissa", "Amanda",
    "Letícia", "Paula", "Priscila", "Patrícia", "Sandra", "Adriana", "Aline", "Amélia",
    "Antonia", "Brenda", "Bruna", "Carla", "Catarina", "Célia", "Daniela", "Debora", "Diana",
    "Dulce", "Eliana", "Elisa", "Emília", "Erika", "Esmeralda", "Fabiana", "Flávia", "Gisele",
    "Glória", "Graciela", "Ingrid", "Inês", "Iara", "Ivete", "Joana", "Juliana", "Karina",
    "Laís", "Lorena", "Luciana", "Luna", "Luzia", "Maitê", "Malu", "Marcela", "Margarida",
    "Marina", "Marta", "Maysa", "Michele", "Natália", "Noemi", "Olga", "Paloma", "Pietra",
    "Raquel", "Renata", "Rita", "Rosa", "Rosana", "Silvia", "Sofia", "Susana", "Tatiana",
    "Teresa", "Thaís", "Valdirene", "Vera", "Alice", "Andressa", "Araceli", "Áurea", "Bela",
    "Belmira", "Bibiana", "Brasiliana", "Brisa", "Chica", "Crisanta", "Dalia", "Daiane",
    "Diolinda", "Dylla", "Efigenia", "Flor", "Fidelis", "Galadriel", "Gilma", "Inez", "Iolanda",
    "Iria", "Isaura", "Ivete", "Iyara", "Jacinda", "Joaninha", "Josefa", "Juanita", "Julinha",
    "Kiana", "Kely", "Leonor", "Liliana", "Lina", "Loíde", "Ludmila", "Madalena", "Mafalda",
    "Manuela", "Mara", "Marilia", "Mariazinha", "Micaela", "Nelinha", "Neves", "Nuria",
    "Pérola", "Poliana", "Quiteria", "Rosalice", "Sara", "Talita", "Telma", "Teresinha",
    "Thailita", "Valéria", "Zilda", "Zoe", "Maria Clara", "Maria Eduarda", "Maria Luísa", "Maria Júlia", "Maria Alice", "Maria Helena",
    "Maria Fernanda", "Maria Vitória", "Maria Cecília", "Maria Sophia", "Maria Isadora",
    "João Pedro", "João Gabriel", "João Lucas", "João Vitor", "João Guilherme", "João Miguel",
    "João Paulo", "João Felipe", "Luiz Fernando", "Luiz Otávio", "Ana Luiza", "Ana Carolina",
    "Ana Clara", "Ana Júlia", "Ana Beatriz", "Ana Sofia", "Ana Vitória", "Pedro Henrique",
    "Carlos Eduardo", "José Augusto", "Antônio Carlos", "Beatriz Helena", "Clara Lívia",
    "Eduardo Henrique", "Enzo Gabriel", "Gabriel Henrique", "Laura Sophia", "Miguel Ângelo",
    "Vitor Hugo"
}


def _clean(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z ]+", "", s).strip()


def score_series(s: pd.Series) -> float:
    n = len(s)
    sample = s.dropna().astype(str).head(500)
    if sample.empty:
        return 0.0
    non_null = sample.size / n
    alpha_pct = np.mean(sample.apply(lambda x: _clean(x).replace(" ", "").isalpha()))
    istitle_pct = np.mean(sample.apply(lambda x: x.istitle()))
    tok2_pct   = np.mean(sample.apply(lambda x: len(x.split()) >= 2))
    len_ok     = np.mean(sample.str.len().between(8, 40))
    dict_pct   = np.mean(sample.apply(lambda x: _clean(x.split()[0]).lower() in BR_NAMES))
    ner_sample = " ".join(sample.sample(min(100, len(sample))))
    doc = NLP(ner_sample)
    person_hits = sum(1 for ent in doc.ents if ent.label_ == "PER")
    ner_pct = person_hits / max(1, len(doc.ents))
    weights = dict(non_null=0.1, alpha=0.15, title=0.15, tok2=0.15,
                   len_ok=0.1, dict=0.15, ner=0.2)
    score = (
        weights["non_null"] * non_null +
        weights["alpha"]    * alpha_pct +
        weights["title"]    * istitle_pct +
        weights["tok2"]     * tok2_pct +
        weights["len_ok"]   * len_ok +
        weights["dict"]     * dict_pct +
        weights["ner"]      * ner_pct
    )
    return score


def detect_name_column(df: pd.DataFrame) -> tuple[str, pd.Series]:
    obj_cols = df.select_dtypes(include="object").columns
    if not len(obj_cols):
        raise ValueError("DataFrame não tem colunas do tipo string.")
    scores = {col: score_series(df[col]) for col in obj_cols}
    best = max(scores, key=scores.get)
    return best, pd.Series(scores, name="score").sort_values(ascending=False)