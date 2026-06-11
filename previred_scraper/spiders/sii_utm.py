import scrapy
from previred_scraper.items import UtmItem


def _clean_number(val):
    if val is None:
        return None
    val = val.strip().replace('\u00a0', '')
    val = val.replace('.', '').replace(',', '.')
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_strip(val):
    if val is None:
        return None
    val = val.strip()
    return val if val else None


class SiiUtmSpider(scrapy.Spider):
    name = 'sii_utm'
    allowed_domains = ['www.sii.cl']
    start_urls = ['https://www.sii.cl/valores_y_fechas/utm/utm2026.htm']

    def parse(self, response):
        rows = response.css('table.tabla tbody tr, table tr')

        if not rows:
            rows = response.xpath('//table[contains(.//th, "UTM")]//tr')

        for row in rows:
            tds = row.css('td, th')
            if len(tds) < 3:
                continue

            cells = [td.css('::text').get('').strip() for td in tds]
            first = cells[0].strip().lower()

            month_map = {
                'enero': 'Enero', 'febrero': 'Febrero', 'marzo': 'Marzo',
                'abril': 'Abril', 'mayo': 'Mayo', 'junio': 'Junio',
                'julio': 'Julio', 'agosto': 'Agosto', 'septiembre': 'Septiembre',
                'octubre': 'Octubre', 'noviembre': 'Noviembre', 'diciembre': 'Diciembre',
            }

            if first not in month_map:
                continue

            item = UtmItem()
            item['mes'] = f"{month_map[first]} 2026"
            item['utm'] = _clean_number(cells[1]) if len(cells) > 1 else None
            item['uta'] = _clean_number(cells[2]) if len(cells) > 2 else None
            item['ipc_puntos'] = _clean_number(cells[3]) if len(cells) > 3 else None
            item['variacion_mensual'] = _safe_strip(cells[4]) if len(cells) > 4 else None
            item['variacion_acumulada'] = _safe_strip(cells[5]) if len(cells) > 5 else None
            item['variacion_anual'] = _safe_strip(cells[6]) if len(cells) > 6 else None

            for var_field in ['variacion_mensual', 'variacion_acumulada', 'variacion_anual']:
                val = item.get(var_field)
                if val and val.replace(',', '').replace('.', '').replace('-', '').strip():
                    if not val.endswith('%'):
                        item[var_field] = val + '%'

            yield item
