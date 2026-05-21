# Poké-Crawler

Crawler assíncrono que extrai dados detalhados de Pokémon do portal **Bulbapedia** e persiste em SQLite.

## Arquitetura

O projeto segue separação clara de responsabilidades em 3 camadas:

```
src/
├── requester.py   # EXTRACT  — Requisições HTTP com retries e backoff
├── parser.py      # TRANSFORM — Parsing do HTML com BeautifulSoup
├── storage.py     # LOAD     — Persistência em SQLite + download de imagens
├── main.py        # Orquestrador assíncrono (semáforo + gather)
└── config.py      # Configurações centralizadas (diretórios, paths)
```

## Decisões Técnicas

| Biblioteca | Motivo |
|------------|--------|
| **aiohttp** | Cliente HTTP assíncrono — permite dezenas de requisições simultâneas sem bloquear o event loop |
| **BeautifulSoup4** | Parsing de HTML tolerante a markup malformado; seletores CSS e navegação na árvore DOM |
| **aiosqlite** | SQLite assíncrono — mesma conveniência do sqlite3 padrão, mas sem travar o event loop |
| **aiofiles** | Escrita de imagens em disco sem bloquear o loop assíncrono |

**Concorrência:** `asyncio.Semaphore(5)` limita a 5 requisições simultâneas para não sobrecarregar o servidor. `asyncio.gather` coordena a execução concorrente de todos os Pokémon.

**Resiliência:** Retry com backoff exponencial (1s, 2s, 4s) em falhas de rede. Se o banco falhar, os dados são salvos em um arquivo **DLQ** (`dlq_falhas_banco.json`) como fallback.

## Pré-requisitos

- Python 3.10+
- `pip`

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Lista padrão (fallback)

```bash
python src/main.py
```

### Arquivo `.txt` com nomes

```bash
python src/main.py --file pokemon_list.txt
```

O arquivo deve ter um nome por linha:

```
Bulbasaur
Charmander
Mewtwo
```

### Nomes direto no terminal

```bash
python src/main.py --names Pikachu Charmander "Mime Jr."
```

## Docker

### Build

```bash
docker build -t pokecrawler .
```

### Execução

```bash
docker run --rm -v "$(pwd)/data:/app/data" pokecrawler
```

### Docker Compose

```bash
docker compose up --build
```

## Output

Após a execução, os arquivos ficam em `./data/`:

```
data/
├── pokedex.db              # Banco SQLite com todos os Pokémon
├── images/                 # Imagens baixadas (.png)
│   ├── bulbasaur.png
│   ├── charmander.png
│   └── ...
└── dlq_falhas_banco.json   # Dados que não puderam ser salvos no banco
```

### Estrutura da tabela `pokemon`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `pokedex_number` | INTEGER (PK) | Número Nacional da Pokédex |
| `name` | TEXT | Nome do Pokémon |
| `category` | TEXT | Categoria (ex: Seed Pokémon) |
| `types` | TEXT | Lista JSON de tipos |
| `hp`, `attack`, `defense`, `sp_atk`, `sp_def`, `speed` | INTEGER | Base Stats |
| `abilities` | TEXT | Lista JSON de habilidades (com flag `is_hidden`) |
| `pre_evolution` | TEXT | Nome do Pokémon antecessor |
| `post_evolution` | TEXT | Nome do Pokémon sucessor |
| `local_image_path` | TEXT | Caminho local da imagem baixada |
