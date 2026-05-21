import argparse
import asyncio
import logging
from pathlib import Path

import aiohttp

import requester
import parser
import storage

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_URL = "https://bulbapedia.bulbagarden.net/wiki/{}_(Pok%C3%A9mon)"
MAX_CONCURRENT_REQUESTS = 5 
DEFAULT_POKEMON = ["Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Squirtle"]


def _load_pokemon_list() -> list[str]:
    parser = argparse.ArgumentParser(description="Poké-Crawler - Extrai dados da Bulbapedia")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", type=str, help="Arquivo .txt com nomes de Pokémon (1 por linha)")
    group.add_argument("--names", nargs="+", help="Nomes dos Pokémon via terminal")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            return [line.strip() for line in f if line.strip()]

    if args.names:
        return args.names

    try:
        with open(Path(__file__).parent.parent / "pokemon_list.txt") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        pass

    logging.warning("Nenhuma lista encontrada. Usando padrão.")
    return DEFAULT_POKEMON


async def process_pokemon(pokemon_name: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> None:
    """
    Pipeline ETL (Extract, Transform, Load) para um único Pokémon.
    """
    formatted_name = pokemon_name.replace(" ", "_")
    url = BASE_URL.format(formatted_name)
    
    async with semaphore:
        logging.info(f"[EXTRACT] Iniciando requisição para {pokemon_name}...")
        
        html_content = await requester.fetch_html(url, session)
        if not html_content:
            logging.warning(f"Abortando pipeline para {pokemon_name} (Falha no Download do HTML).")
            return

        logging.info(f"[TRANSFORM] Realizando parsing de {pokemon_name}...")
        
        pokemon_data = parser.parse_pokemon_data(html_content)
        if not pokemon_data:
            logging.warning(f"Abortando pipeline para {pokemon_name} (Falha no Parsing).")
            return

        logging.info(f"[LOAD] Baixando imagem e salvando dados de {pokemon_name}...")
        
        image_url = pokemon_data.get('image_url')
        local_path = None
        if image_url:
            local_path = await storage.download_image(image_url, pokemon_name, session)

        await storage.save_pokemon_data(pokemon_data, local_image_path=local_path)
            
        logging.info(f"Pipeline concluído com sucesso para {pokemon_name}!\n")

async def main(pokemon_list: list[str]) -> None:
    """
    Função principal que orquestra todo o sistema.
    """
    logging.info("Iniciando o Poké-Crawler...")
    
    await storage.init_db()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for pokemon in pokemon_list:
            task = asyncio.create_task(process_pokemon(pokemon, session, semaphore))
            tasks.append(task)
            
        await asyncio.gather(*tasks)
        
    logging.info("Scraping de todos os Pokémon finalizado com sucesso!")

if __name__ == "__main__":
    pokemon_list = _load_pokemon_list()
    asyncio.run(main(pokemon_list))
