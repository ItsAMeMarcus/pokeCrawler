import aiohttp
import asyncio
import logging

async def fetch_html(url: str, session: aiohttp.ClientSession, retries: int = 3) -> str | None:
    """
    Faz a requisição HTTP assíncrona para uma URL.
    Possui sistema de 'retries' (tentativas) caso a rede falhe.
    """
    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                response.raise_for_status() 
                return await response.text()
                
        except Exception as e:
            logging.warning(f"Erro ao acessar {url}: {e}. Tentativa {attempt + 1} de {retries}")
            
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                
    logging.error(f"Falha definitiva ao acessar {url} após {retries} tentativas.")
    return None
