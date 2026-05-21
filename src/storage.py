import asyncio
import aiosqlite
import logging
import json
import re
import aiofiles
import os
import aiohttp
import config

async def init_db() -> None:
    """
    Cria o arquivo do banco de dados e a tabela se não existirem.
    Esta função deve ser chamada apenas uma vez, quando o programa iniciar.
    """
    await asyncio.to_thread(os.makedirs, config.DATA_DIR, exist_ok=True)
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pokemon (
                pokedex_number INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                types TEXT,
                hp INTEGER,
                attack INTEGER,
                defense INTEGER,
                sp_atk INTEGER,
                sp_def INTEGER,
                speed INTEGER,
                abilities TEXT,
                pre_evolution TEXT,
                post_evolution TEXT,
                local_image_path TEXT
            )
        ''')
        await db.commit()
        logging.info("Banco de dados inicializado com sucesso.")

async def save_pokemon_data(pokemon_data: dict, local_image_path: str | None = None) -> None:
    """
    Insere ou atualiza os dados do Pokémon no banco de dados SQLite.
    """
    if not pokemon_data:
        logging.warning("Nenhum dado recebido para salvar no banco.")
        return

    types_json = json.dumps(pokemon_data.get('types', []))
    abilities_json = json.dumps(pokemon_data.get('abilities', []))
    
    stats = pokemon_data.get('base_stats', {})
    evos = pokemon_data.get('evolutions', {})

    query = '''
        INSERT OR REPLACE INTO pokemon (
            pokedex_number, name, category, types,
            hp, attack, defense, sp_atk, sp_def, speed,
            abilities, pre_evolution, post_evolution, local_image_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    values = (
        pokemon_data.get('pokedex_number'),
        pokemon_data.get('name'),
        pokemon_data.get('category'),
        types_json,
        stats.get('hp'),
        stats.get('attack'),
        stats.get('defense'),
        stats.get('sp_atk'),
        stats.get('sp_def'),
        stats.get('speed'),
        abilities_json,
        evos.get('pre_evolution'),
        evos.get('post_evolution'),
        local_image_path 
    )

    try:
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(query, values)
            await db.commit()
            logging.info(f"Pokémon #{pokemon_data.get('pokedex_number')} salvo no banco!")
            
    except Exception as e:
        logging.error(f"Erro fatal no banco para {pokemon_data.get('name')}: {e}. Salvando no arquivo de falhas (DLQ)...")
        
        try:
            async with aiofiles.open(config.DLQ_PATH, mode="a", encoding="utf-8") as dlq_file:
                await dlq_file.write(json.dumps(pokemon_data) + "\n")
        except Exception as dlq_error:
            logging.critical(f"Falha catastrófica: Não foi possível salvar nem no banco nem no DLQ. Erro: {dlq_error}")

def _sanitize_filename(filename: str) -> str:
    """
    Remove caracteres perigosos do nome do arquivo para evitar Path Traversal.
    Permite apenas letras, números, hífens e sublinhados.
    """
    no_spaces = filename.replace(' ', '_')
    clean_name = re.sub(r'[^\w\-]', '', no_spaces)
    
    return clean_name.lower()

async def download_image(image_url: str, pokemon_name: str, session: aiohttp.ClientSession) -> str | None:
    """
    Faz o download da imagem de forma assíncrona e salva no disco de forma segura.
    Recebe a sessão do aiohttp para reaproveitar a conexão (melhor performance).
    """
    if not image_url:
        logging.warning(f"URL de imagem inválida para {pokemon_name}.")
        return None

    safe_name = _sanitize_filename(pokemon_name)
    
    save_dir = str(config.IMAGES_DIR)
    await asyncio.to_thread(os.makedirs, save_dir, exist_ok=True)
    
    file_path = os.path.join(save_dir, f"{safe_name}.png")

    try:
        async with session.get(image_url) as response:
            response.raise_for_status()
            async with aiofiles.open(file_path, mode='wb') as f:
                await f.write(await response.read())
                
            logging.info(f"Imagem de {pokemon_name} salva com sucesso em {file_path}")
            return file_path 
            
    except aiohttp.ClientError as e:
        logging.exception(f"Erro de rede ao baixar imagem de {pokemon_name}: {e}")
    except OSError as e:
        logging.exception(f"Erro de permissão/disco ao salvar imagem de {pokemon_name}: {e}")
    except Exception as e:
        logging.exception(f"Erro inesperado no download da imagem de {pokemon_name}: {e}")
        
    return None
