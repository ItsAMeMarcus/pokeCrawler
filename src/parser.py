from bs4 import BeautifulSoup
import logging

def parse_pokemon_data(html_content: str) -> dict | None:
    """
    Função principal que orquestra a extração de dados do HTML do Pokémon.
    Delega a extração de cada seção para funções privadas (Clean Code: Single Responsibility).
    """
    if not html_content:
        logging.warning("Conteúdo HTML vazio recebido para parsing.")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    try:
        pokemon_data = {
            "name": _extract_name(soup),
            "pokedex_number": _extract_pokedex_number(soup),
            "category": _extract_category(soup),
            "types": _extract_types(soup),
            "base_stats": _extract_base_stats(soup),
            "abilities": _extract_abilities(soup),
            "evolutions": _extract_evolutions(soup),
            "image_url": _extract_image_url(soup)
        }
        return pokemon_data
    except Exception as e:
        logging.exception(f"Erro inesperado durante o parsing do HTML: {e}")
        return None


def _extract_name(soup: BeautifulSoup) -> str:
    """Extrai o nome do Pokémon."""
    name_tag = soup.select_one('big b')
    
    if not name_tag:
        return "Unknown"
        
    return name_tag.text.strip()

def _extract_pokedex_number(soup: BeautifulSoup) -> int | None:
    """Extrai o Número Nacional da Pokédex e normaliza para inteiro."""
    number_tag = soup.select_one('th.roundy span')
    
    if not number_tag:
        return None
        
    try:
        clean_number = number_tag.text.replace('#', '').strip()
        return int(clean_number)
    except ValueError as e:
        logging.warning(f"Erro ao normalizar o número da Pokédex: {e}")
        return None

def _extract_category(soup: BeautifulSoup) -> str:
    """Extrai a categoria do Pokémon (ex: Seed Pokémon)."""
    category_tag = soup.select_one('a[title="Pokémon category"]')
    
    if not category_tag:
        return "Unknown"
        
    return category_tag.text.strip()

def _extract_abilities(soup: BeautifulSoup) -> list[dict]:
    """
    Extrai a lista de habilidades, identificando qual é a Hidden Ability.
    Retorna uma lista de dicionários.
    """
    abilities: list[dict] = []
    
    ability_anchor = soup.select_one('a[href="/wiki/Ability"]')
    
    if not ability_anchor:
        return abilities
        
    parent_td = ability_anchor.find_parent('td')
    if not parent_td:
        return abilities
        
    inner_table = parent_td.find('table')
    if not inner_table:
        return abilities
        
    td_tags = inner_table.find_all('td')
    
    for td in td_tags:
        style = td.get('style')
        
        if style and isinstance(style, str) and 'display: none' in style:
            continue
            
        a_tag = td.find('a')
        if not a_tag:
            continue
            
        ability_name = a_tag.text.strip()
        if not ability_name:
            continue
            
        is_hidden = 'Hidden Ability' in td.text
        
        ability_entry = {"name": ability_name, "is_hidden": is_hidden}
        if ability_entry not in abilities:
            abilities.append(ability_entry)
            
    return abilities

def _extract_evolutions(soup: BeautifulSoup) -> dict:
    """Extrai o nome do Pokémon antecessor e sucessor, se houverem."""
    evolutions = {
        "pre_evolution": None, 
        "post_evolution": None
    }
    
    current_node = soup.select_one('a.mw-selflink')
    if not current_node:
        return evolutions
        
    current_table = current_node.find_parent('table')
    if not current_table:
        return evolutions
        
    current_card_cell = current_table.find_parent('td')
    if not current_card_cell:
        return evolutions
        
    prev_cell = current_card_cell.find_previous_sibling('td')
    
    if prev_cell and '→' in prev_cell.text:
        prev_cell = prev_cell.find_previous_sibling('td')
        
    if prev_cell:
        prev_link = prev_cell.select_one('a[title]')
        if prev_link:
            evolutions["pre_evolution"] = prev_link.text.strip()
            
    next_cell = current_card_cell.find_next_sibling('td')
    
    if next_cell and '→' in next_cell.text:
        next_cell = next_cell.find_next_sibling('td')
        
    if next_cell:
        next_link = next_cell.select_one('a[title]')
        if next_link:
            evolutions["post_evolution"] = next_link.text.strip()
            
    return evolutions

def _extract_image_url(soup: BeautifulSoup) -> str | None:
    """
    Extrai a URL da imagem principal do Pokémon a partir da infobox.
    Garante que a URL seja absoluta e pronta para download.
    """
    img_tag = soup.select_one('a.mw-file-description img')
    
    if not img_tag:
        return None
        
    image_url = img_tag.get('src')
    
    if not image_url or not isinstance(image_url, str):
        return None
        
    if image_url.startswith('//'):
        image_url = f"https:{image_url}"
        
    return image_url


def _extract_types(soup: BeautifulSoup) -> list[str]:
    """
    Extrai apenas os tipos principais do Pokémon, ignorando a tabela de efetividade.
    Usa o padrão de 'Âncora e Contêiner' para isolar o escopo da busca.
    """
    types = []
    
    type_label = soup.select_one('a[href="/wiki/Type"][title="Type"]')
    
    if not type_label:
        return types
        
    parent_row = type_label.find_parent('tr')
    
    if not parent_row:
        return types
        
    type_tags = parent_row.select('a[href$="_(type)"]')
    
    for tag in type_tags:
        type_name = tag.text.strip()
        if type_name and type_name != "Unknown" and type_name not in types:
            types.append(type_name)
            
    return types

def _extract_base_stats(soup: BeautifulSoup) -> dict:
    """Extrai os atributos base usando links diretos e Guard Clauses (Fail Fast)."""
    stat_selectors = {
        "hp": "/wiki/HP",
        "attack": "/wiki/Stat#Attack",
        "defense": "/wiki/Stat#Defense",
        "sp_atk": "/wiki/Stat#Special_Attack",
        "sp_def": "/wiki/Stat#Special_Defense",
        "speed": "/wiki/Stat#Speed"
    }
    
    base_stats = {
        "hp": 0, "attack": 0, "defense": 0,
        "sp_atk": 0, "sp_def": 0, "speed": 0
    }
    
    for key, href in stat_selectors.items():
        try:
            a_tag = soup.select_one(f'a[href="{href}"]')
            if not a_tag:
                continue  
                
            th_tag = a_tag.find_parent('th')
            if not th_tag:
                continue
                
            divs = th_tag.find_all('div', recursive=False)
            if len(divs) < 2:
                continue
                
            raw_value = divs[1].text.strip()
            base_stats[key] = int(raw_value)
            
        except ValueError as e:
            logging.warning(f"Erro ao converter o valor de {key}: {e}")
            
    return base_stats
