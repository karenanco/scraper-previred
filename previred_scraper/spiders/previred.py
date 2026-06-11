import re
import io
import pdfplumber
import scrapy

from previred_scraper.items import PreviredItem


MONTHS_ES = {
    'enero': 'Enero', 'febrero': 'Febrero', 'marzo': 'Marzo',
    'abril': 'Abril', 'mayo': 'Mayo', 'junio': 'Junio',
    'julio': 'Julio', 'agosto': 'Agosto', 'septiembre': 'Septiembre',
    'octubre': 'Octubre', 'noviembre': 'Noviembre', 'diciembre': 'Diciembre',
}

MONTH_LIST = list(MONTHS_ES.values())


def _clean(val):
    if val is None:
        return None
    val = val.strip().replace('\u00a0', ' ')
    val = re.sub(r'\s+', ' ', val)
    return val


def _parse_chilean_number(text):
    if not text:
        return None
    text = text.strip().replace('$', '').replace('%', '').strip()
    text = text.replace('.', '')
    text = text.replace(',', '.')
    try:
        if text.startswith('(') and text.endswith(')'):
            text = '-' + text[1:-1]
        return float(text)
    except (ValueError, TypeError):
        return None


def _find_money(text, start=0):
    idx = text.find('$', start)
    if idx == -1:
        return None
    rest = text[idx + 1:].strip()
    m = re.match(r'([\d]{1,3}(?:\.?\d{3})*(?:,\d+)?)', rest)
    if m:
        return _parse_chilean_number(m.group(1))
    return None


def _find_all_money(text):
    result = []
    start = 0
    while True:
        idx = text.find('$', start)
        if idx == -1:
            break
        rest = text[idx + 1:].strip()
        m = re.match(r'([\d]{1,3}(?:\.?\d{3})*(?:,\d+)?)', rest)
        if m:
            result.append(_parse_chilean_number(m.group(1)))
            start = idx + len(m.group(0))
        else:
            start = idx + 1
    return result


def _name_from_url(url):
    for name in MONTH_LIST:
        if name in url:
            return name
    return None


def _parse_text_page(text):
    item = PreviredItem()

    periodo = re.search(
        r'cotizaciones\s+a\s+pagar\s+en\s+(\w+\s+\d{4}).*?remuneraciones\s+(\w+\s+\d{4})',
        text, re.IGNORECASE
    )
    if periodo:
        item['periodo_remuneracion'] = _clean(periodo.group(2))

    uf_section = re.search(r'VALOR UF(.*?)(?:RENTAS TOPES|TASA COTIZACIÓN)', text, re.DOTALL | re.IGNORECASE)
    if uf_section:
        uf_text = uf_section.group(1)
        vals = _find_all_money(uf_text)
        if vals:
            item['uf_valor'] = vals[0]
        fecha_m = re.search(r'Al\s+(\d+\s+de\s+\w+\s+del?\s+\d{4})', uf_text)
        if fecha_m:
            item['uf_fecha'] = _clean(fecha_m.group(1))

    rt_section = re.search(r'RENTAS TOPES IMPONIBLES(.*?)TASA COTIZACIÓN', text, re.DOTALL | re.IGNORECASE)
    if rt_section:
        vals = _find_all_money(rt_section.group(1))
        if len(vals) >= 1:
            item['renta_tope_afp'] = vals[0]
        if len(vals) >= 2:
            item['renta_tope_ips'] = vals[1]
        if len(vals) >= 3:
            item['renta_tope_cesantia'] = vals[2]

    afp_section = re.search(
        r'TASA COTIZACIÓN AFP(.*?)(?:SEGURO DE CESANTÍA|AHORRO PREVISIONAL)',
        text, re.DOTALL | re.IGNORECASE
    )
    if afp_section:
        afp_text = afp_section.group(1)
        afps = ['Capital', 'Cuprum', 'Habitat', 'PlanVital', 'ProVida', 'Modelo', 'Uno']
        afp_tasas = {}
        for afp in afps:
            m = re.search(
                r'{}\s*\n\s*([\d,]+%)\s*\n\s*([\d,]+%)\s*\n\s*([\d,]+%)\s*\n\s*([\d,]+%)'.format(
                    re.escape(afp)
                ),
                afp_text
            )
            if m:
                afp_tasas[afp] = {
                    'trabajador': m.group(1),
                    'empleador': m.group(2),
                    'total': m.group(3),
                    'independiente': m.group(4),
                }
        item['afp_tasas'] = afp_tasas or None

    apv_idx = text.find('AHORRO PREVISIONAL VOLUNTARIO')
    if apv_idx >= 0:
        apv_text = text[apv_idx:apv_idx + 500]
        vals = _find_all_money(apv_text)
        if len(vals) >= 1:
            item['apv_tope_mensual'] = vals[0]
        if len(vals) >= 2:
            item['apv_tope_anual'] = vals[1]

    dc_idx = text.find('DEPÓSITO CONVENIDO')
    if dc_idx >= 0:
        dc_text = text[dc_idx:dc_idx + 300]
        vals = _find_all_money(dc_text)
        if vals:
            item['deposito_convenido_tope'] = vals[0]

    utm_section = re.search(
        r'(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto)\s+\d{4}\s*.*?\$[\s]*([\d.,]+).*?\$[\s]*([\d.,]+)',
        text
    )
    if utm_section:
        item['utm_valor'] = _parse_chilean_number(utm_section.group(2))
        item['uta_valor'] = _parse_chilean_number(utm_section.group(3))

    rm_section = re.search(
        r'RENTAS MÍNIMAS IMPONIBLES(.*?)(?:SEGURO SOCIAL|SEGURO DE INVALIDEZ|DISTRIBUCIÓN)',
        text, re.DOTALL | re.IGNORECASE
    )
    if rm_section:
        vals = _find_all_money(rm_section.group(1))
        if len(vals) >= 1:
            item['renta_minima_dependientes'] = vals[0]
        if len(vals) >= 2:
            item['renta_minima_menores'] = vals[1]
        if len(vals) >= 3:
            item['renta_minima_casa_particular'] = vals[2]
        if len(vals) >= 4:
            item['renta_minima_no_remuneracional'] = vals[3]

    ss = re.search(r'SEGURO SOCIAL.*?([\d.,]+%)', text, re.DOTALL | re.IGNORECASE)
    if ss:
        item['seguro_social_tasa'] = _clean(ss.group(1))

    sis = re.search(r'Tasa SIS\s*\n\s*([\d.,]+%)', text)
    if not sis:
        sis = re.search(r'SIS\s*\n\s*([\d.,]+%)', text)
    if sis:
        item['sis_tasa'] = _clean(sis.group(1))

    salud_ccaf = re.search(r'CCAF\s*\n\s*([\d.,]+%[^A-Z]*)', text)
    if salud_ccaf:
        item['salud_ccaf'] = _clean(salud_ccaf.group(1))

    salud_fonasa = re.search(r'FONASA\s*\n\s*([\d.,]+%[^A-Z]*)', text)
    if salud_fonasa:
        item['salud_fonasa'] = _clean(salud_fonasa.group(1))

    af_idx = text.find('ASIGNACIÓN FAMILIAR')
    if af_idx >= 0:
        af_text = text[af_idx:af_idx + 600]
        tramos = {}
        lines = af_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = re.match(r'^(\d)\s*\(([A-D])\)$', line)
            if m:
                tramo_key = f"{m.group(1)} ({m.group(2)})"
                monto = None
                requisito = None
                if i + 1 < len(lines):
                    mont_str = lines[i + 1].strip()
                    if mont_str.startswith('$') or mont_str.startswith('–'):
                        monto = mont_str
                if i + 2 < len(lines):
                    req_str = lines[i + 2].strip()
                    if 'Renta' in req_str:
                        requisito = req_str
                if monto:
                    tramos[tramo_key] = {'monto': monto, 'requisito': requisito}
                i += 3
            else:
                i += 1
        item['asignacion_familiar'] = tramos or None

    return item


class PreviredSpider(scrapy.Spider):
    name = 'previred'
    allowed_domains = ['www.previred.com', 'previred.com']
    start_urls = ['https://www.previred.com/indicadores-previsionales/']

    def parse(self, response):
        page_text = response.css('body').xpath('string(.)').getall()
        full_text = '\n'.join(page_text)

        item = _parse_text_page(full_text)
        periodo = item.get('periodo_remuneracion', '')
        mes_actual = ''
        if periodo:
            parts = periodo.split()
            if parts:
                mes_actual = f"{parts[0].capitalize()} 2026"
        item['mes'] = mes_actual
        yield item

        pdf_links = response.css('a[href*="Indicadores-Previsionales"][href$=".pdf"]::attr(href)').getall()
        pdf_links = [u for u in pdf_links if '2026' in u]

        seen = set()
        for url in pdf_links:
            abs_url = response.urljoin(url)
            if abs_url in seen:
                continue
            seen.add(abs_url)
            yield scrapy.Request(abs_url, callback=self.parse_pdf, dont_filter=True)

    def parse_pdf(self, response):
        try:
            with pdfplumber.open(io.BytesIO(response.body)) as pdf:
                all_tables = []
                pdf_text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pdf_text += page_text + '\n'
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)

            item = PreviredItem()

            periodo = re.search(
                r'remuneraciones\s+(\w+\s+\d{4})', pdf_text, re.IGNORECASE
            )
            if periodo:
                item['periodo_remuneracion'] = _clean(periodo.group(1))

            for table in all_tables:
                self._parse_pdf_table(table, item)

            url_name = response.url.split('/')[-1]
            mes_pdf = _name_from_url(url_name)
            if not mes_pdf:
                periodo = item.get('periodo_remuneracion', '')
                if periodo:
                    parts = periodo.split()
                    if parts:
                        mes_pdf = parts[0].capitalize()
            if mes_pdf:
                item['mes'] = f"{mes_pdf} 2026"

            if item.get('mes'):
                yield item
        except Exception as e:
            self.logger.warning('Failed to parse PDF %s: %s', response.url, e)

    def _parse_pdf_table(self, table, item):
        if not table or not table[0]:
            return
        header = ' '.join(str(c or '') for c in table[0]).lower()

        if 'valor uf' in header:
            for row in table[1:]:
                cells = [str(c or '') for c in row]
                row_text = ' '.join(cells)

                if not item.get('uf_fecha'):
                    m = re.search(r'Al\s+(\d+\s+de\s+\w+\s+del?\s+\d{4})\s*:', row_text)
                    if m:
                        item['uf_fecha'] = _clean(m.group(1))

                vals = _find_all_money(row_text)
                if not item.get('uf_valor') and vals:
                    item['uf_valor'] = vals[0]
                if not item.get('utm_valor') and len(vals) >= 2:
                    item['utm_valor'] = vals[1]
                if not item.get('uta_valor') and len(vals) >= 3:
                    item['uta_valor'] = vals[2]

        elif 'rentas topes' in header or 'rentas mínimas' in header:
            tope_labels_map = {
                'afp': 'renta_tope_afp',
                'inp': 'renta_tope_ips',
                'ips': 'renta_tope_ips',
                'cesant': 'renta_tope_cesantia',
            }
            minima_labels_map = {
                'dependiente': 'renta_minima_dependientes',
                'menores': 'renta_minima_menores',
                'casa particular': 'renta_minima_casa_particular',
                'no remuneracional': 'renta_minima_no_remuneracional',
            }
            for row in table[1:]:
                cells = [str(c or '') for c in row]
                for ci in range(0, len(cells) - 1, 2):
                    label_cell = cells[ci]
                    value_cell = cells[ci + 1]
                    if not label_cell or not value_cell:
                        continue
                    label_lines = label_cell.split('\n')
                    value_lines = value_cell.split('\n')
                    for li, label_line in enumerate(label_lines):
                        label_line = label_line.strip()
                        if not label_line:
                            continue
                        ll = label_line.lower()
                        field = None
                        for kw, f in tope_labels_map.items():
                            if kw in ll:
                                field = f
                                break
                        if not field:
                            for kw, f in minima_labels_map.items():
                                if kw in ll:
                                    field = f
                                    break
                        if field and not item.get(field):
                            vv = _find_all_money(label_line)
                            if not vv and li < len(value_lines):
                                vv = _find_all_money(value_lines[li])
                            if vv:
                                item[field] = vv[0]

        elif 'tasa cotizaci' in header:
            afps = ['Capital', 'Cuprum', 'Habitat', 'PlanVital', 'ProVida', 'Modelo', 'Uno']
            afp_tasas = item.get('afp_tasas') or {}
            for row in table[1:]:
                cells = [str(c or '') for c in row]
                if not cells:
                    continue
                for raw in cells[0].split('\n'):
                    raw = raw.strip()
                    if not raw:
                        continue
                    first = raw.split()[0] if raw.split() else ''
                    if first in afps or first.lower() in [a.lower() for a in afps]:
                        vals = re.findall(r'([\d,]+%)', raw)
                        if len(vals) < 4:
                            for c in cells[1:]:
                                ms = re.findall(r'([\d,]+%)', c)
                                vals.extend(ms)
                        if len(vals) >= 4:
                            canonical = next(a for a in afps if a.lower() == first.lower())
                            afp_tasas[canonical] = {
                                'trabajador': vals[0],
                                'empleador': vals[1],
                                'total': vals[2],
                                'independiente': vals[3],
                            }
                row_text = ' '.join(cells).lower()
                if 'expectativa' in row_text and not item.get('seguro_social_tasa'):
                    right_vals = re.findall(r'([\d.,]+%)', ' '.join(cells[5:]))
                    if right_vals:
                        item['seguro_social_tasa'] = right_vals[-1]
                if 'tasa sis' in row_text and not item.get('sis_tasa'):
                    right_vals = re.findall(r'([\d.,]+%)', ' '.join(cells[5:]))
                    if right_vals:
                        item['sis_tasa'] = right_vals[0]
                if row_text.strip().startswith('ccaf') and not item.get('salud_ccaf'):
                    m = re.search(r'([\d.,]+%[^a-z]*)', ' '.join(cells[5:]))
                    if m:
                        item['salud_ccaf'] = _clean(m.group(1))
                if row_text.strip().startswith('fonasa') and not item.get('salud_fonasa'):
                    m = re.search(r'([\d.,]+%[^a-z]*)', ' '.join(cells[5:]))
                    if m:
                        item['salud_fonasa'] = _clean(m.group(1))
            if afp_tasas:
                item['afp_tasas'] = afp_tasas

        elif 'ahorro' in header or 'apv' in header:
            for row in table[1:]:
                cells = [str(c or '') for c in row]
                row_text = ' '.join(cells)
                if 'tope mensual' in row_text.lower():
                    v = _find_money(cells[1]) if cells[1:] and cells[1].strip() else _find_money(row_text)
                    if v:
                        item['apv_tope_mensual'] = v
                if 'tope anual' in row_text.lower() and '600' in row_text:
                    v = _find_money(cells[1]) if cells[1:] else _find_money(row_text)
                    if v:
                        item['apv_tope_anual'] = v
                if ('tope anual' in row_text.lower() and '900' in row_text) or \
                   (('depósito' in row_text.lower() or 'deposito' in row_text.lower()) and not item.get('deposito_convenido_tope')):
                    if cells[1] and cells[1].strip():
                        v = _find_money(cells[1])
                    else:
                        v = _find_money(row_text)
                    if v:
                        item['deposito_convenido_tope'] = v
                for cell in cells:
                    m = re.match(r'\s*(\d)\s*\(([A-D])\)', cell)
                    if m:
                        vals = _find_all_money(cell)
                        tramo_key = f"{m.group(1)} ({m.group(2)})"
                        monto = None
                        if vals:
                            monto = f"$ {vals[0]:,.0f}".replace(',', '.')
                        requisito = None
                        rm = re.search(r'Renta.*?\$[\s]*([\d.,]+)', cell)
                        if rm:
                            req_val = _parse_chilean_number(rm.group(1))
                            if req_val:
                                requisito = f"Renta $ {req_val:,.0f}".replace(',', '.')
                        af_dict = item.get('asignacion_familiar') or {}
                        if monto:
                            af_dict[tramo_key] = {'monto': monto, 'requisito': requisito}
                        item['asignacion_familiar'] = af_dict or None
