import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

EXCEL_PATH = Path(__file__).parent.parent / 'data' / 'indicadores.xlsx'
MONTHS_ORDER = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

st.set_page_config(
    page_title='Previred - Indicadores Previsionales 2026',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

CUSTOM_CSS = """
<style>
    .stApp { background-color: #f8f9fa; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3 { font-family: 'Inter', -apple-system, sans-serif; }
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e9ecef;
        text-align: center;
        height: 100%;
    }
    .kpi-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #6c757d;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #212529;
        line-height: 1.2;
    }
    .kpi-delta {
        font-size: 0.7rem;
        color: #6c757d;
        margin-top: 0.2rem;
    }
    .tramo-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid #e9ecef;
        margin-bottom: 0.5rem;
    }
    .tramo-title {
        font-size: 1rem;
        font-weight: 600;
        color: #1a73e8;
    }
    .tramo-monto {
        font-size: 1.1rem;
        font-weight: 700;
    }
    .tramo-req {
        font-size: 0.75rem;
        color: #6c757d;
    }
    .footer-text {
        text-align: center;
        color: #adb5bd;
        font-size: 0.75rem;
        padding-top: 1rem;
    }
    div[data-testid="stDataFrame"] { border: none; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
        font-weight: 500;
    }
</style>
"""

CURRENCY_COLS = {'renta_tope_afp', 'renta_tope_ips', 'renta_tope_cesantia',
                 'apv_tope_mensual', 'apv_tope_anual', 'deposito_convenido_tope',
                 'utm_valor', 'uta_valor', 'renta_minima_dependientes',
                 'renta_minima_menores', 'renta_minima_casa_particular',
                 'renta_minima_no_remuneracional'}


def _parse_json(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def fmt_currency(val):
    if pd.isna(val) or val is None:
        return '—'
    return f"${val:,.0f}".replace(',', '.')


def fmt_uf(val):
    if pd.isna(val) or val is None:
        return '—'
    return f"${val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_pct(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return '—'
    s = str(val)
    return s.replace('R.I.', '').strip()


def sort_months(df):
    if 'mes' not in df.columns or df.empty:
        return df
    def sort_key(m):
        parts = str(m).split()
        if len(parts) >= 1:
            try:
                return MONTHS_ORDER.index(parts[0])
            except ValueError:
                return 99
        return 99
    df = df.copy()
    df['_sort'] = df['mes'].apply(sort_key)
    df = df.sort_values('_sort').drop(columns='_sort')
    return df


@st.cache_data
def load_data():
    if not EXCEL_PATH.exists():
        return None, None
    prev = pd.read_excel(EXCEL_PATH, sheet_name='Previred')
    utm = pd.read_excel(EXCEL_PATH, sheet_name='UTM_UTA')

    for col in ['afp_tasas', 'asignacion_familiar']:
        if col in prev.columns:
            prev[col] = prev[col].apply(_parse_json)
    prev = prev.dropna(how='all')
    prev = sort_months(prev)

    if utm is not None and not utm.empty:
        utm = utm.dropna(how='all')
        utm = sort_months(utm)

    return prev, utm


def get_last(prev_df, field):
    val = prev_df[field].dropna()
    return val.iloc[-1] if not val.empty else None


def kpi_card(label, value, delta_text=None, color='#212529'):
    delta_html = f'<div class="kpi-delta">{delta_text}</div>' if delta_text else ''
    return f'''
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color};">{value}</div>
        {delta_html}
    </div>'''


def render_kpi_row(prev_df, utm_df):
    last_mes = prev_df['mes'].iloc[-1] if not prev_df.empty else ''
    cols = st.columns(6)

    with cols[0]:
        uf = get_last(prev_df, 'uf_valor')
        uf_fecha = get_last(prev_df, 'uf_fecha')
        st.markdown(kpi_card('UF', fmt_uf(uf) if uf else '—', str(uf_fecha) if uf_fecha else ''), unsafe_allow_html=True)

    with cols[1]:
        utm_val = get_last(utm_df, 'utm') if utm_df is not None else None
        utm_mes = utm_df['mes'].iloc[-1] if utm_df is not None and not utm_df.empty else ''
        st.markdown(kpi_card('UTM', fmt_currency(utm_val) if utm_val else '—', str(utm_mes)), unsafe_allow_html=True)

    with cols[2]:
        uta_val = get_last(utm_df, 'uta') if utm_df is not None else None
        st.markdown(kpi_card('UTA', fmt_currency(uta_val) if uta_val else '—', str(utm_mes)), unsafe_allow_html=True)

    with cols[3]:
        tope_val = get_last(prev_df, 'renta_tope_afp')
        st.markdown(kpi_card('Tope AFP (90 UF)', fmt_currency(tope_val) if tope_val else '—', last_mes, '#1a73e8'), unsafe_allow_html=True)

    with cols[4]:
        tope_ips = get_last(prev_df, 'renta_tope_ips')
        st.markdown(kpi_card('Tope IPS (60 UF)', fmt_currency(tope_ips) if tope_ips else '—', last_mes, '#2e7d32'), unsafe_allow_html=True)

    with cols[5]:
        tope_ces = get_last(prev_df, 'renta_tope_cesantia')
        st.markdown(kpi_card('Tope Seg. Cesantía', fmt_currency(tope_ces) if tope_ces else '—', last_mes, '#e65100'), unsafe_allow_html=True)


def tab_resumen(prev_df, utm_df):
    st.subheader('Resumen Ejecutivo')
    render_kpi_row(prev_df, utm_df)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown('##### Últimos Valores Clave')
        data = {
            'Indicador': ['UF', 'UTM', 'UTA', 'Tope AFP (90 UF)', 'Tope IPS (60 UF)',
                          'Tope Seg. Cesantía', 'APV Tope Mensual', 'APV Tope Anual',
                          'Seguro Social', 'SIS', 'Salud CCAF', 'Salud FONASA'],
        }
        vals_list = []
        if not prev_df.empty:
            r = prev_df.iloc[-1]
            vals_list = [
                fmt_uf(r.get('uf_valor')), fmt_currency(r.get('utm_valor')),
                fmt_currency(r.get('uta_valor')), fmt_currency(r.get('renta_tope_afp')),
                fmt_currency(r.get('renta_tope_ips')), fmt_currency(r.get('renta_tope_cesantia')),
                fmt_currency(r.get('apv_tope_mensual')), fmt_currency(r.get('apv_tope_anual')),
                fmt_pct(r.get('seguro_social_tasa')), fmt_pct(r.get('sis_tasa')),
                fmt_pct(r.get('salud_ccaf')), fmt_pct(r.get('salud_fonasa')),
            ]
        data['Valor'] = vals_list if vals_list else ['—'] * 12
        idx = pd.Index([''] * len(data['Indicador']))
        st.dataframe(
            pd.DataFrame(data, index=idx),
            use_container_width=True,
            hide_index=True,
            column_config={
                'Indicador': st.column_config.TextColumn('Indicador', width='medium'),
                'Valor': st.column_config.TextColumn(f'{prev_df.iloc[-1]["mes"] if not prev_df.empty else ""}', width='small'),
            }
        )

    with c2:
        st.markdown('##### Renta Mínima Imponible')
        data = {
            'Categoría': ['Dependientes', 'Menores 18 / Mayores 65',
                          'Casa Particular', 'No Remuneracional'],
        }
        rm_vals = []
        if not prev_df.empty:
            r = prev_df.iloc[-1]
            rm_vals = [
                fmt_currency(r.get('renta_minima_dependientes')),
                fmt_currency(r.get('renta_minima_menores')),
                fmt_currency(r.get('renta_minima_casa_particular')),
                fmt_currency(r.get('renta_minima_no_remuneracional')),
            ]
        data['Valor'] = rm_vals if rm_vals else ['—'] * 4
        idx = pd.Index([''] * len(data['Categoría']))
        st.dataframe(
            pd.DataFrame(data, index=idx),
            use_container_width=True,
            hide_index=True,
        )


def tab_evolucion(prev_df, utm_df):
    st.subheader('Evolución Mensual de Indicadores')

    cols_to_plot = {
        'Valores UF y Topes': ['uf_valor', 'renta_tope_afp', 'renta_tope_ips', 'renta_tope_cesantia'],
        'Rentas Mínimas': ['renta_minima_dependientes', 'renta_minima_menores',
                           'renta_minima_casa_particular', 'renta_minima_no_remuneracional'],
        'APV y Depósito Convenido': ['apv_tope_mensual', 'apv_tope_anual', 'deposito_convenido_tope'],
    }
    labels = {
        'uf_valor': 'UF', 'renta_tope_afp': 'Tope AFP', 'renta_tope_ips': 'Tope IPS',
        'renta_tope_cesantia': 'Tope Cesantía',
        'renta_minima_dependientes': 'Mín. Dependientes', 'renta_minima_menores': 'Mín. <18/>65',
        'renta_minima_casa_particular': 'Mín. Casa Particular', 'renta_minima_no_remuneracional': 'Mín. No Remun.',
        'apv_tope_mensual': 'APV Mensual', 'apv_tope_anual': 'APV Anual', 'deposito_convenido_tope': 'Dep. Convenido',
    }
    colors = ['#1a73e8', '#e65100', '#2e7d32', '#6a1b9a', '#00838f', '#c62828', '#f9a825', '#4e342e']

    for section, plot_cols in cols_to_plot.items():
        available = [c for c in plot_cols if c in prev_df.columns and prev_df[c].notna().sum() > 1]
        if not available:
            continue
        df_plot = prev_df[['mes'] + available].copy()
        df_plot = df_plot.set_index('mes')
        fig = go.Figure()
        for i, col in enumerate(available):
            color = colors[i % len(colors)]
            fig.add_trace(go.Scatter(
                x=df_plot.index, y=df_plot[col],
                mode='lines+markers',
                name=labels.get(col, col),
                line=dict(width=2.5, color=color),
                marker=dict(size=7, color=color),
                hovertemplate='%{x}<br>%{y:$,.0f}<extra></extra>'
            ))
        fig.update_layout(
            title=dict(text=section, font=dict(size=16)),
            xaxis=dict(title='', tickangle=-45),
            yaxis=dict(title='CLP', tickformat='$,.0f'),
            hovermode='x unified',
            margin=dict(l=20, r=20, t=40, b=40),
            height=350,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Inter, sans-serif'),
        )
        fig.update_xaxes(gridcolor='#f0f0f0')
        fig.update_yaxes(gridcolor='#f0f0f0')
        st.plotly_chart(fig, use_container_width=True)

    if utm_df is not None and not utm_df.empty:
        st.subheader('UTM - SII')
        utm_plot = utm_df[['mes', 'utm']].dropna().copy()
        if not utm_plot.empty:
            utm_plot = utm_plot.set_index('mes')
            fig = px.bar(
                utm_plot, x=utm_plot.index, y='utm',
                labels={'utm': 'UTM', 'index': ''},
                color_discrete_sequence=['#1a73e8'],
            )
            fig.update_traces(marker=dict(line=dict(width=0)), hovertemplate='%{x}<br>$%{y:,.0f}<extra></extra>')
            fig.update_layout(
                xaxis=dict(tickangle=-45),
                yaxis=dict(title='CLP', tickformat='$,.0f'),
                margin=dict(l=20, r=20, t=10, b=40),
                height=300,
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=False,
            )
            fig.update_xaxes(gridcolor='#f0f0f0')
            fig.update_yaxes(gridcolor='#f0f0f0')
            st.plotly_chart(fig, use_container_width=True)


def tab_afp(prev_df):
    st.subheader('Tasas de Cotización AFP')
    meses_disponibles = prev_df[prev_df['afp_tasas'].notna()]['mes'].tolist()
    if not meses_disponibles:
        st.info('No hay datos de tasas AFP disponibles.')
        return

    mes_selected = st.selectbox('Seleccionar Mes', meses_disponibles, index=len(meses_disponibles) - 1)
    row = prev_df[prev_df['mes'] == mes_selected].iloc[0]
    afp_data = row.get('afp_tasas')
    if not afp_data or not isinstance(afp_data, dict):
        st.info('Datos de AFP no disponibles para este mes.')
        return

    tasa_rows = []
    for afp, tasas in afp_data.items():
        if isinstance(tasas, dict):
            tasa_rows.append({
                'AFP': afp,
                'Trabajador': tasas.get('trabajador', ''),
                'Empleador': tasas.get('empleador', ''),
                'Total': tasas.get('total', ''),
                'Independiente': tasas.get('independiente', ''),
            })
    df_tasas = pd.DataFrame(tasa_rows)

    c1, c2 = st.columns([2, 1])
    with c1:
        st.dataframe(df_tasas, use_container_width=True, hide_index=True,
                     column_config={col: st.column_config.TextColumn(col, width='small') for col in df_tasas.columns})

    with c2:
        fig = go.Figure()
        colors_palette = px.colors.qualitative.Set2
        for i, col in enumerate(['Trabajador', 'Empleador', 'Total', 'Independiente']):
            vals = []
            for v in df_tasas[col]:
                try:
                    vals.append(float(v.replace('%', '').replace(',', '.')))
                except (ValueError, AttributeError):
                    vals.append(0)
            fig.add_trace(go.Bar(
                name=col, x=df_tasas['AFP'], y=vals,
                marker_color=colors_palette[i % len(colors_palette)],
                hovertemplate='%{x}<br>%{y:.2f}%<extra></extra>',
            ))
        fig.update_layout(
            barmode='group',
            title=dict(text=f'{mes_selected}', font=dict(size=14)),
            yaxis=dict(title='Tasa (%)', ticksuffix='%'),
            margin=dict(l=20, r=20, t=30, b=80),
            height=350,
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation='h', y=-0.25),
        )
        fig.update_xaxes(gridcolor='#f0f0f0')
        fig.update_yaxes(gridcolor='#f0f0f0')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('##### Tasas de Seguros')
    c_s1, c_s2, c_s3 = st.columns(3)
    with c_s1:
        st.markdown(kpi_card('Seguro Social', fmt_pct(row.get('seguro_social_tasa')),
                             mes_selected, '#00838f'), unsafe_allow_html=True)
    with c_s2:
        st.markdown(kpi_card('SIS', fmt_pct(row.get('sis_tasa')),
                             mes_selected, '#6a1b9a'), unsafe_allow_html=True)
    with c_s3:
        st.markdown(kpi_card('Salud CCAF / FONASA',
                             f"{fmt_pct(row.get('salud_ccaf'))} / {fmt_pct(row.get('salud_fonasa'))}",
                             mes_selected, '#2e7d32'), unsafe_allow_html=True)


def tab_asignacion(prev_df):
    st.subheader('Asignación Familiar - Tramos')
    meses_disponibles = prev_df[prev_df['asignacion_familiar'].notna()]['mes'].tolist()
    if not meses_disponibles:
        st.info('No hay datos de asignación familiar disponibles.')
        return

    mes_selected = st.selectbox('Seleccionar Mes', meses_disponibles,
                                index=len(meses_disponibles) - 1, key='af_mes')
    row = prev_df[prev_df['mes'] == mes_selected].iloc[0]
    af_data = row.get('asignacion_familiar')
    if not af_data or not isinstance(af_data, dict):
        st.info('Datos no disponibles para este mes.')
        return

    st.markdown(f'<div style="font-size:0.9rem;color:#6c757d;margin-bottom:0.8rem;">{mes_selected}</div>',
                unsafe_allow_html=True)

    tramo_info = {
        '1 (A)': {'color': '#1a73e8', 'desc': 'Ingresos más bajos'},
        '2 (B)': {'color': '#2e7d32', 'desc': 'Ingresos medios-bajos'},
        '3 (C)': {'color': '#e65100', 'desc': 'Ingresos medios'},
        '4 (D)': {'color': '#6c757d', 'desc': 'Sin asignación'},
    }
    tramos = sorted(af_data.items(), key=lambda x: x[0])

    cards_html = '<div style="display:flex;flex-wrap:wrap;gap:0.8rem;">'
    for tramo_key, vals in tramos:
        info = tramo_info.get(tramo_key, {'color': '#212529', 'desc': ''})
        monto = vals.get('monto', '') if isinstance(vals, dict) else ''
        req = vals.get('requisito', '') if isinstance(vals, dict) else ''
        cards_html += f'''
        <div class="tramo-card" style="flex:1;min-width:200px;border-top:3px solid {info['color']};">
            <div class="tramo-title">{tramo_key}</div>
            <div style="font-size:0.7rem;color:#6c757d;">{info['desc']}</div>
            <div class="tramo-monto">{monto}</div>
            <div class="tramo-req">{req}</div>
        </div>'''
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    af_rows = []
    for tramo_key, vals in tramos:
        if isinstance(vals, dict):
            af_rows.append({
                'Tramo': tramo_key,
                'Monto': vals.get('monto', ''),
                'Requisito de Renta': vals.get('requisito', ''),
            })
    if af_rows:
        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(af_rows), use_container_width=True, hide_index=True)


def tab_datos(prev_df, utm_df):
    st.subheader('Tabla Completa - Indicadores Previred')
    display_cols = [
        'mes', 'periodo_remuneracion', 'uf_valor', 'uf_fecha',
        'renta_tope_afp', 'renta_tope_ips', 'renta_tope_cesantia',
        'apv_tope_mensual', 'apv_tope_anual', 'deposito_convenido_tope',
        'utm_valor', 'uta_valor',
        'renta_minima_dependientes', 'renta_minima_menores',
        'renta_minima_casa_particular', 'renta_minima_no_remuneracional',
        'seguro_social_tasa', 'sis_tasa', 'salud_ccaf', 'salud_fonasa',
    ]
    available = [c for c in display_cols if c in prev_df.columns]
    df_display = prev_df[available].copy()

    for col in df_display.select_dtypes(include=['float64', 'int64']).columns:
        if col in CURRENCY_COLS:
            df_display[col] = df_display[col].apply(
                lambda x: f"${x:,.0f}".replace(',', '.') if pd.notna(x) else '')
        elif col == 'uf_valor':
            df_display[col] = df_display[col].apply(
                lambda x: fmt_uf(x) if pd.notna(x) else '')

    rename_map = {
        'mes': 'Mes', 'periodo_remuneracion': 'Periodo',
        'uf_valor': 'Valor UF', 'uf_fecha': 'Fecha UF',
        'renta_tope_afp': 'Tope AFP', 'renta_tope_ips': 'Tope IPS',
        'renta_tope_cesantia': 'Tope Cesantía',
        'apv_tope_mensual': 'APV Mensual', 'apv_tope_anual': 'APV Anual',
        'deposito_convenido_tope': 'Dep. Convenido',
        'utm_valor': 'UTM', 'uta_valor': 'UTA',
        'renta_minima_dependientes': 'R.Mín. Dependientes',
        'renta_minima_menores': 'R.Mín. <18/>65',
        'renta_minima_casa_particular': 'R.Mín. Casa Particular',
        'renta_minima_no_remuneracional': 'R.Mín. No Remunerac.',
        'seguro_social_tasa': 'Seg. Social', 'sis_tasa': 'SIS',
        'salud_ccaf': 'CCAF', 'salud_fonasa': 'FONASA',
    }
    df_display = df_display.rename(columns=rename_map)

    col_config = {}
    for c in df_display.columns:
        if c in ('Valor UF',):
            col_config[c] = st.column_config.TextColumn(c, width='small')
        elif c in ('Tope AFP', 'Tope IPS', 'Tope Cesantía', 'APV Mensual', 'APV Anual', 'Dep. Convenido'):
            col_config[c] = st.column_config.TextColumn(c, width='small')
        elif c == 'Fecha UF':
            col_config[c] = st.column_config.TextColumn(c, width='small')
        elif c in ('Seg. Social', 'SIS', 'CCAF', 'FONASA'):
            col_config[c] = st.column_config.TextColumn(c, width='small')
        elif c in ('UTM', 'UTA'):
            col_config[c] = st.column_config.TextColumn(c, width='small')

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
    )

    if utm_df is not None and not utm_df.empty:
        st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
        st.subheader('UTM / UTA / IPC - SII')
        utm_display = utm_df.copy()
        for col in ['utm', 'uta']:
            if col in utm_display.columns:
                utm_display[col] = utm_display[col].apply(
                    lambda x: fmt_currency(x) if pd.notna(x) else '')

        rename_utm = {
            'mes': 'Mes', 'utm': 'UTM', 'uta': 'UTA',
            'variacion_mensual': 'Var. Mensual', 'variacion_acumulada': 'Var. Acumulada',
            'variacion_anual': 'Var. Anual',
        }
        utm_display = utm_display.rename(columns=rename_utm)
        cols_available = [c for c in ['Mes', 'UTM', 'UTA', 'Var. Mensual', 'Var. Acumulada', 'Var. Anual']
                          if c in utm_display.columns]
        st.dataframe(utm_display[cols_available], use_container_width=True, hide_index=True)


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    prev_df, utm_df = load_data()

    with st.sidebar:
        st.markdown('<div style="text-align:center;padding:0.5rem 0;">'
                    '<span style="font-size:2rem;">📊</span>'
                    '<h3 style="margin:0.3rem 0 0;">Previred</h3>'
                    '<p style="font-size:0.8rem;color:#6c757d;">Indicadores Previsionales</p>'
                    '</div>', unsafe_allow_html=True)
        st.markdown('---')

        if prev_df is not None and not prev_df.empty:
            meses = prev_df['mes'].tolist()
            sel_meses = st.multiselect(
                'Filtrar por Mes',
                meses,
                default=meses,
                placeholder='Seleccionar meses...',
            )
            if sel_meses:
                prev_df = prev_df[prev_df['mes'].isin(sel_meses)].copy()
                if not prev_df.empty:
                    prev_df = sort_months(prev_df)

            st.markdown('---')
            st.markdown(f'**📅 Meses con datos:** {len(prev_df)}')
            st.markdown(f'**🔢 Columnas:** {len([c for c in prev_df.columns if prev_df[c].notna().any()])}')
            st.markdown(f'**📄 Fuente:** Previred + SII')
        else:
            st.warning('No hay datos disponibles.')

        st.markdown('---')
        st.markdown('<div style="text-align:center;font-size:0.75rem;color:#adb5bd;">'
                    'Actualizado: '
                    + (datetime.fromtimestamp(EXCEL_PATH.stat().st_mtime).strftime('%d-%m-%Y %H:%M')
                       if EXCEL_PATH.exists() else '—')
                    + '</div>', unsafe_allow_html=True)

    if prev_df is None or prev_df.empty:
        st.warning('Aún no hay datos. Ejecuta primero: `python run_scraper.py`')
        return

    st.title('📊 Indicadores Previsionales 2026')
    st.markdown(
        f'<p style="color:#6c757d;margin-top:-0.5rem;">'
        f'Datos de {prev_df.iloc[0]["mes"]} a {prev_df.iloc[-1]["mes"]} · '
        f'{len(prev_df)} meses disponibles</p>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        '📋 Resumen',
        '📈 Evolución',
        '🏦 Tasas AFP',
        '👨‍👩‍👧‍👦 Asignación Familiar',
        '📄 Datos Completos',
    ])

    with tab1:
        tab_resumen(prev_df, utm_df)
    with tab2:
        tab_evolucion(prev_df, utm_df)
    with tab3:
        tab_afp(prev_df)
    with tab4:
        tab_asignacion(prev_df)
    with tab5:
        tab_datos(prev_df, utm_df)

    st.markdown('<div class="footer-text">'
                'Datos obtenidos de <a href="https://www.previred.com/indicadores-previsionales/">Previred</a> '
                'y <a href="https://www.sii.cl/valores_y_fechas/utm/utm2026.htm">SII</a>. '
                'Actualización diaria vía cron job.</div>',
                unsafe_allow_html=True)


if __name__ == '__main__':
    main()
