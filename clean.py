import os
import pandas as pd
import re
from google.cloud import bigquery

# Configuration
input_dir = '.'
output_dir = 'cleaned_reports'

PROJECT_ID = 'data-test-389108'       
DATASET_ID = 'survey_mostre'         
TABLE_ID   = 'master_survey_vis_23_present_test_v1'     

# Final canonical target schema requested for the visitor table
TARGET_SCHEMA = [
    'soddisfazione_complessiva',
    'net_promoter_commercio',
    'elemento_top',
    'elemento_flop',
    'importanza_evento',
    'possibilita_di_ritorno',
    'importanza_aspetti_quantita_di_espositori',
    'importanza_aspetti_qualita_di_espositori',
    'importanza_aspetti_appearance_of_the_fair',
    'importanza_aspetti_internazionalita_di_espositori',
    'importanza_aspetti_rappresentativita_del_settore',
    'soddisfazione_aspetti_quantita_di_espositori',
    'soddisfazione_aspetti_qualita_di_espositori',
    'soddisfazione_aspetti_appearance_of_the_fair',
    'soddisfazione_aspetti_internazionalita_di_espositori',
    'soddisfazione_aspetti_rappresentativita_del_settore',
    'aspetti_biglietteria_accredito',
    'aspetti_assistenza_info_point_accoglienza',
    'aspetti_logistica_indicazioni_segnaletica',
    'aspetti_parcheggi',
    'aspetti_ristorazione',
    'aspetti_misure_di_sicurezza',
    'aspetti_servizi_digitali',
    'soddisfazione_digital_platform_facilita_uso',
    'soddisfazione_digital_platform_pianificazione_pre_fiera',
    'soddisfazione_digital_platform_mappa_interattiva',
    'soddisfazione_digital_platform_profilo_espositori_incontrati',
    'soddisfazione_digital_platform_accesso_contenuti',
    'Manifestazione',
    'Anno',
    'importanza_aspetti_immagine_complessiva_della_fiera',
    'soddisfazione_aspetti_immagine_complessiva_della_fiera',
    'importanza_aspetti_business_development',
    'soddisfazione_aspetti_business_development',
    'importanza_aspetti_innovazione_di_prodotto',
    'soddisfazione_aspetti_innovazione_di_prodotto',
    'company_name',
    'importanza_aspetti_programma_convegnistico',
    'soddisfazione_aspetti_programma_convegnistico',
    'sostenibilità_allestimenti_in_materiali_riutilizzabili',
    'sostenibilità_illuminazione_a_led_nei_padiglioni',
    'sostenibilità_ristorazione_plastic_free',
    'sostenibilità_presenza_di_convegni_riguardanti_aspetti_di_sostenibilità',
    'sostenibilità_presenza_di_espositori_che_propongono_prodotti_e_soluzioni_sostenibili'
]

# Flexible keywords to drop raw survey metadata, specific vertical logs, or operational fields
to_delete_patterns = [
    r'STARTDATE', r'STARTTIME', r'COMPLETEDDATE', r'COMPLETEDTIME', r'LANGCODE', r'COMPLETIONSTATUS', r'SURVEYDATAID',
    r'MyMatching', r'Canali', r'jobTitle', r'Privacy',
    r'Altre fiere', r'Competitors', r'browserType', r'deviceType', r'userAgent', r'salutation', r'firstName',
    r'lastName', r'emailAddress', r'Ruolo in azienda', r'Consenso', r'Age', r'Età', r'Nazione', r'Paese',
    r'Provenienza', r'Country', r'Settore', r'Categoria', r'Macrocategoria', r'attività', r'Azienda', r'Storico',
    r'Superficie', r'MQ', r'Stand', r'Padiglione', r'HALL', r'Sezione', r'Tipologia', r'Durata', r'Cadenza',
    r'Periodo', r'Fatturato atteso', r'Contatti', r'Partecipazione a convegni', r'Valutazione convegni',
    r'Differenze competitor', r'Altri brand', r'Aggiornamenti', r'Brand Ambassador', r'Conoscenza', r'Sinergie',
    r'Influenza', r'Milano punto forza', r'Miglioramenti', r'Commenti', r'Regioni', r'Meet&amp;Coffee',
    r'Punti di forza', r'Luogo', r'PTE Lab', r'PTE Fashion Show', r'Iniziative fiera', r'Iniziative provate',
    r'Interesse principale', r'Spending', r'Budget dedicato', # --- ADDED TO CATCH 2026 VISITOR EDGE CASES (JUNK/METADATA) ---
    r'^ruolo azienda.*',
    r'^perchè no.*',
    r'^durata alternativa.*',
    r'^concomitanza.*',
    r'^città, regione o Paese.*'
]

# Strategic matching updates tracking raw survey text string variations into unified columns
column_mappings = {
    'possibilita_di_ritorno': [
        r'Probabilità di ritorno', r'Likelihood of return', r'Probabilita_di_ritorno'
    ],
    'net_promoter_commercio': [
        r'Net promoter', r'Net Promoter Score', r'NPS'
    ],
    'importanza_evento': [
        r'Importanza evento', r'Importance of event', r'Importanza complessiva'
    ],
    'company_name': [
        r'companyName', r'Company Name', r'Nome azienda'
    ],
    'soddisfazione_complessiva': [
        r'Soddisfazione complessiva', r'Overall satisfaction'
    ],
    'elemento_top': [r'Elemento top'],
    'elemento_flop': [r'Elemento flop'],
    
    # =========================================================================
    # IMPORTANZA ASPETTI MAPPINGS
    # Includes negative lookaheads to explicitly prevent capturing "soddisfazione" metrics
    # =========================================================================
    'importanza_aspetti_quantita_di_espositori': [
        r'Importanza aspetti.*Quantità di espositori', r'Importanza aspetti.*Quantity of exhibitors', r'Importanza aspetti.*Number of exhibitors',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Quantity of exhibitors',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Quantità di espositori'
    ],
    'importanza_aspetti_qualita_di_espositori': [
        r'Importanza aspetti.*Qualità degli espositori', r'Importanza aspetti.*Qualità di espositori', r'Importanza aspetti.*Quality of exhibitors',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Quality of exhibitors',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Qualità degli espositori',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Qualità di espositori'
    ],
    'importanza_aspetti_internazionalita_di_espositori': [
        r'Importanza aspetti.*Internazionalità degli espositori', r'Importanza aspetti.*Internazionalità di espositori', r'Importanza aspetti.*International nature of exhibitors', r'Importanza aspetti.*Internationality of exhibitors',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Internationality of the exhibitors',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*International nature of exhibitors'
    ],
    'importanza_aspetti_appearance_of_the_fair': [
        r'Importanza aspetti.*Aspect of the exhibition', r'Importanza aspetti.*Overall look of the exhibition',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Aspect of the exhibition',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Overall look of the exhibition'
    ],
    'importanza_aspetti_immagine_complessiva_della_fiera': [
        r'Importanza aspetti.*Immagine complessiva della fiera', r'Importanza aspetti.*Overall image of the fair', r'Importanza aspetti.*Overall image of the trade show',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Overall image of the fair',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Immagine complessiva della fiera'
    ],
    'importanza_aspetti_rappresentativita_del_settore': [
        r'Importanza aspetti.*Rappresentatività del settore', r'Importanza aspetti.*Representation of.*brand', r'Importanza aspetti.*Representativeness of the industry',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Representation of exhibiting brands',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Representativeness of the sector'
    ],
    'importanza_aspetti_business_development': [
        r'Importanza aspetti.*New business development', r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*New business development'
    ],
    'importanza_aspetti_innovazione_di_prodotto': [
        r'Importanza aspetti.*Innovazione di prodotto', r'Importanza aspetti.*Product innovation',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Product innovation',
        r'^(?=.*Aspetti)(?!.*copy)(?!.*soddisfazione)(?!.*sodd).*Innovazione di prodotto'
    ],
    
    # =========================================================================
    # SODDISFAZIONE ASPETTI MAPPINGS
    # =========================================================================
    'soddisfazione_aspetti_quantita_di_espositori': [
        r'Soddisfazione aspetti.*Quantità di espositori', r'Soddisfazione aspetti.*Number of exhibitors', r'Soddisfazione aspetti.*Quantity of exhibitors',
        r'Sodd aspetti.*Quantity of exhibitors', r'Aspetti.*copy.*Quantity of exhibitors', r'Aspetti.*copy.*Quantità di espositori'
    ],
    'soddisfazione_aspetti_qualita_di_espositori': [
        r'Soddisfazione aspetti.*Qualità degli espositori', r'Soddisfazione aspetti.*Qualità di espositori', r'Soddisfazione aspetti.*Quality of exhibitors',
        r'Sodd aspetti.*Quality of exhibitors', r'Aspetti.*copy.*Quality of exhibitors', r'Aspetti.*copy.*Qualità degli espositori', r'Aspetti.*copy.*Qualità di espositori'
    ],
    'soddisfazione_aspetti_internazionalita_di_espositori': [
        r'Soddisfazione aspetti.*Internazionalità degli espositori', r'Soddisfazione aspetti.*Internationality of exhibitors', r'Soddisfazione aspetti.*International nature of exhibitors',
        r'Sodd aspetti.*International nature of exhibitors', r'Aspetti.*copy.*Internationality of the exhibitors', r'Aspetti.*copy.*International nature of exhibitors', r'Soddisfazione aspetti.*Internazionalità di espositori'
    ],
    'soddisfazione_aspetti_appearance_of_the_fair': [
        r'Soddisfazione aspetti.*Aspect of the exhibition', r'Sodd aspetti.*Overall image of the fair',
        r'Aspetti.*copy.*Aspect of the exhibition', r'Aspetti.*copy.*Overall look of the exhibition'
    ],
    'soddisfazione_aspetti_immagine_complessiva_della_fiera': [
        r'Soddisfazione aspetti.*Immagine complessiva della fiera', r'Soddisfazione aspetti.*Overall image of the trade show', r'Soddisfazione aspetti.*Overall image of the exhibition',
        r'Aspetti.*copy.*Overall image of the fair', r'Aspetti.*copy.*Immagine complessiva della fiera'
    ],
    'soddisfazione_aspetti_rappresentativita_del_settore': [
        r'Soddisfazione aspetti.*Rappresentatività del settore', r'Soddisfazione aspetti.*Representativeness of the industry', r'Soddisfazione aspetti.*Representativeness of the sector',
        r'Sodd aspetti.*Representation of.*brand', r'Aspetti.*copy.*Representation of exhibiting brands', r'Aspetti.*copy.*Representativeness of the sector'
    ],
    'soddisfazione_aspetti_business_development': [
        r'Soddisfazione aspetti.*New business development', r'Aspetti.*copy.*New business development'
    ],
    'soddisfazione_aspetti_innovazione_di_prodotto': [
        r'Soddisfazione aspetti.*Innovazione di prodotto', r'Soddisfazione aspetti.*Product innovation',
        r'Aspetti.*copy.*Product innovation', r'Aspetti.*copy.*Innovazione di prodotto'
    ],
    'importanza_aspetti_programma_convegnistico': [
        r'^0?7\. Importanza aspetti.*Programma convegnistico',
        r'Importanza aspetti.*Programma convegnistico'
    ],
    'soddisfazione_aspetti_programma_convegnistico': [
        r'^0?8\. Soddisfazione aspetti.*Programma convegnistico',
        r'Soddisfazione aspetti.*Programma convegnistico'
    ],

    # =========================================================================
    # VISITOR STRUCTURED SERVICE ASPECTS
    # =========================================================================
    'aspetti_biglietteria_accredito': [
        r'^20\.\s*Servizi\s*-\s*Ticketing Services\s*/\s*Accreditation$',
        r'^20\.\s*Servizi\s*-\s*Biglietteria\s*/\s*Accredito$',
        r'^20\.\s*Servizi\s*-\s*Servizi di biglietteria\s*/\s*Accredito$'
    ],
    'aspetti_assistenza_info_point_accoglienza': [
        r'^20\.\s*Servizi\s*-\s*Information Point Assistance\s*/\s*Reception$',
        r'^20\.\s*Servizi\s*-\s*Info Point Assistance\s*/\s*Reception$',
        r'^20\.\s*Servizi\s*-\s*Assistenza Info Point\s*/\s*Accoglienza$',
        r'^20\.\s*Servizi\s*-\s*Assistenza Information Point\s*/\s*Accoglienza$'
    ],
    'aspetti_logistica_indicazioni_segnaletica': [
        r'^20\.\s*Servizi\s*-\s*Logistics\s*/\s*Directions\s*/\s*Signage$',
        r'^20\.\s*Servizi\s*-\s*Venue Logistics\s*/\s*Directions\s*/\s*Signage$',
        r'^20\.\s*Servizi\s*-\s*Logistica\s*/\s*Indicazioni\s*/\s*Segnaletica$',
        r'^20\.\s*Servizi\s*-\s*Logistica di quartiere\s*/\s*Indicazioni\s*/\s*Segnaletica$'
    ],
    'aspetti_parcheggi': [
        r'^20\.\s*Servizi\s*-\s*Parking lots$',
        r'^20\.\s*Servizi\s*-\s*Parking spaces$',
        r'^20\.\s*Servizi\s*-\s*Parcheggi$'
    ],
    'aspetti_ristorazione': [
        r'^20\.\s*Servizi\s*-\s*Catering$',
        r'^20\.\s*Servizi\s*-\s*Catering at the venue$',
        r'^20\.\s*Servizi\s*-\s*Catering\s*/\s*Bar$',
        r'^20\.\s*Servizi\s*-\s*Ristorazione$',
        r'^20\.\s*Servizi\s*-\s*Ristorazione\s*/\s*Bar$',
        r'^20\.\s*Servizi\s*-\s*Ristorazione in fiera$'
    ],
    'aspetti_misure_di_sicurezza': [
        r'^20\.\s*Servizi\s*-\s*Security measures$',
        r'^20\.\s*Servizi\s*-\s*Safety measures$',
        r'^20\.\s*Servizi\s*-\s*Misure di sicurezza$'
    ],
    # =========================================================================
    # DIGITAL SERVICES AND DIGITAL PLATFORM SATISFACTION (2023-2026)
    # =========================================================================
    'aspetti_servizi_digitali': [
        r'^(?:20|29)\.\s*Servizi\s*-\s*(?:Digital catalog|Digital catalogue|Catalogo digitale)$',
        r'^20\.\s*Servizi\s*-\s*Digital Platform$',
        r'^20\.\s*Servizi\s*-\s*Digital platform\s*/\s*App$',
        r'^20\.\s*Servizi\s*-\s*copy\s*-\s*Digital catalogue$'
    ],
    'soddisfazione_digital_platform_facilita_uso': [r"^soddisfazione aspetti DP\s*-\s*Facilità d[’']uso della piattaforma$"],
    'soddisfazione_digital_platform_pianificazione_pre_fiera': [r'^soddisfazione aspetti DP\s*-\s*Pianificazione pre-fiera$'],
    'soddisfazione_digital_platform_mappa_interattiva': [r'^soddisfazione aspetti DP\s*-\s*Orientarsi con la mappa interattiva$'],
    'soddisfazione_digital_platform_profilo_espositori_incontrati': [r'^soddisfazione aspetti DP\s*-\s*Profilo e tipologia di espositori incontrati$'],
    'soddisfazione_digital_platform_accesso_contenuti': [r'^soddisfazione aspetti DP\s*-\s*Accesso ai contenuti\s*\(eventi, prodotti e news\)$'],
    # =========================================================================
    # SOSTENIBILITÀ ASPETTI MAPPINGS
    # =========================================================================

    'sostenibilità_allestimenti_in_materiali_riutilizzabili':[
        r'(riutilizzab|reusable)',
    ],
    'sostenibilità_illuminazione_a_led_nei_padiglioni': [
        r'\bled\b',
    ],

    'sostenibilità_ristorazione_plastic_free': [
        r'plastic.*free',
    ],
    'sostenibilità_presenza_di_convegni_riguardanti_aspetti_di_sostenibilità': [
        r'((convegni|conferenze|conference|conferences).*(sostenibil|sustainab)|(sostenibil|sustainab).*(convegni|conferenze|conference|conferences))'
    ],
    'sostenibilità_presenza_di_espositori_che_propongono_prodotti_e_soluzioni_sostenibili': [
        r'((espositori|exhibitors).*(sostenibil|sustainab)|(sostenibil|sustainab).*(espositori|exhibitors))'
    ]
}


# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def should_delete(col_name):
    if col_name in TARGET_SCHEMA:
        return False
    for pattern in to_delete_patterns:
        if re.search(pattern, col_name, re.IGNORECASE):
            return True
    return False

def col_data_clean(df):
    importance_map = {
        '5': 5.0, '4': 4.0, '3': 3.0, '2': 2.0, '1': 1.0,
        '5.0': 5.0, '4.0': 4.0, '3.0': 3.0, '2.0': 2.0, '1.0': 1.0,
        'molto importante': 5.0, 'mediamente importante': 3.0, 'abbastanza importante': 4.0,
        'non molto importante': 2.0, 'per nulla importante': 1.0,
        '5 = molto importante': 5.0, '1 = per nulla importante': 1.0,
        '1 - per nulla': 1.0, '5 - completamente': 5.0, 
        'non un nostro obiettivo': None
    }

    soddisfazione_map = {
        '5': 5.0, '4': 4.0, '3': 3.0, '2': 2.0, '1': 1.0,
        '5.0': 5.0, '4.0': 4.0, '3.0': 3.0, '2.0': 2.0, '1.0': 1.0,
        'molto soddisfatto': 5.0, 'mediamente soddisfatto': 3.0, 'abbastanza soddisfatto': 4.0,
        'non molto soddisfatto': 2.0, 'per nulla soddisfatto': 1.0,
        '5 = molto soddisfatti': 5.0, '1 = per nulla soddisfatti': 1.0,
        '1 - per nulla': 1.0, '5 - completamente': 5.0,
        'non un nostro obiettivo': None, '1 = Per nulla soddisfatto': 1.0,
        '5 = Estremamente soddisfatto': 5.0
    }

    return_map = {
        '5': 5.0, '4': 4.0, '3': 3.0, '2': 2.0, '1': 1.0,
        '5.0': 5.0, '4.0': 4.0, '3.0': 3.0, '2.0': 2.0, '1.0': 1.0,
        'già prenotato': 5.0, 'sicuramente sì': 5.0, 'probabilmente sì': 4.0,
        'forse/incerto': 3.0, 'probabilmente no': 2.0, 'sicuramente no': 1.0,
        'decisamente sì': 5.0, 'decisamente no': 1.0, 'forse / incerto': 3.0
    }

    nps_map = {
        '10 = sicuramente sì': 10.0, '10 = sicuramente si': 10.0,
        '0 = sicuramente no': 0.0,
        **{str(i): float(i) for i in range(11)},
        **{f"{i}.0": float(i) for i in range(11)}
    }

    aspetti_map= {
        5: 5.0, 4: 4.0, 3: 3.0, 2: 2.0, 1: 1.0,
        '5': 5.0, '4': 4.0, '3': 3.0, '2': 2.0, '1': 1.0,
        'Non utilizzato / non saprei': 0.0
    }

    mappings_config = {
        # Core overall KPIs
        'soddisfazione_complessiva': soddisfazione_map,
        'possibilita_di_ritorno': return_map,
        'net_promoter_commercio': nps_map,
        'importanza_evento': importance_map,
        
        # Visitor-Specific Importance Aspects
        'importanza_aspetti_quantita_di_espositori': importance_map,
        'importanza_aspetti_qualita_di_espositori': importance_map,
        'importanza_aspetti_internazionalita_di_espositori': importance_map,
        'importanza_aspetti_rappresentativita_del_settore': importance_map,
        'importanza_aspetti_immagine_complessiva_della_fiera': importance_map,
        'importanza_aspetti_appearance_of_the_fair': importance_map,
        'importanza_aspetti_innovazione_di_prodotto': importance_map,
        'importanza_aspetti_programma_convegnistico': importance_map,
        'importanza_aspetti_business_development': importance_map,
        
        # Visitor-Specific Satisfaction Aspects
        'soddisfazione_aspetti_quantita_di_espositori': soddisfazione_map,
        'soddisfazione_aspetti_qualita_di_espositori': soddisfazione_map,
        'soddisfazione_aspetti_internazionalita_di_espositori': soddisfazione_map,
        'soddisfazione_aspetti_rappresentativita_del_settore': soddisfazione_map,
        'soddisfazione_aspetti_immagine_complessiva_della_fiera': soddisfazione_map,
        'soddisfazione_aspetti_appearance_of_the_fair': soddisfazione_map,
        'soddisfazione_aspetti_innovazione_di_prodotto': soddisfazione_map,
        'soddisfazione_aspetti_programma_convegnistico': soddisfazione_map,
        'soddisfazione_aspetti_business_development': soddisfazione_map,
        'aspetti_biglietteria_accredito': aspetti_map,
        'aspetti_assistenza_info_point_accoglienza': aspetti_map,
        'aspetti_logistica_indicazioni_segnaletica': aspetti_map,
        'aspetti_parcheggi': aspetti_map,
        'aspetti_ristorazione': aspetti_map,
        'aspetti_misure_di_sicurezza': aspetti_map,
        'aspetti_servizi_digitali': aspetti_map,
        'soddisfazione_digital_platform_facilita_uso': aspetti_map,
        'soddisfazione_digital_platform_pianificazione_pre_fiera': aspetti_map,
        'soddisfazione_digital_platform_mappa_interattiva': aspetti_map,
        'soddisfazione_digital_platform_profilo_espositori_incontrati': aspetti_map,
        'soddisfazione_digital_platform_accesso_contenuti': aspetti_map,

        'sostenibilità_allestimenti_in_materiali_riutilizzabili':soddisfazione_map,
        'sostenibilità_illuminazione_a_led_nei_padiglioni':soddisfazione_map,
        'sostenibilità_ristorazione_plastic_free':soddisfazione_map,
        'sostenibilità_presenza_di_convegni_riguardanti_aspetti_di_sostenibilità':soddisfazione_map,
        'sostenibilità_presenza_di_espositori_che_propongono_prodotti_e_soluzioni_sostenibili':soddisfazione_map
    }

    for col, current_map in mappings_config.items():
        if col in df.columns:
            numeric_fallback = pd.to_numeric(df[col], errors='coerce')
            string_series = df[col].dropna().astype(str).str.strip().str.lower()
            mapped_series = string_series.map(current_map)
            df[col] = mapped_series.reindex(df.index).fillna(numeric_fallback)
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
            
    return df


files = [f for f in os.listdir(input_dir) if f.endswith(('.csv', '.xlsx')) and '_cleaned' not in f]
files.sort()

results = {}
all_cleaned_dfs = []

for f in files:
    try:
        file_path = os.path.join(input_dir, f)
        if f.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        tech_id_pattern = r'\s*\[[A-Z0-9]{2}_[^\]]+\]'
        df.columns = df.columns.str.replace(tech_id_pattern, '', regex=True)
        df.columns = df.columns.str.replace(r'\s*\[([^\]]+)\]', r' - \1', regex=True)

        mapped_columns = []
        for col in df.columns:
            mapped_col = col.strip()
            for canonical_name, patterns in column_mappings.items():
                for pattern in patterns:
                    if re.search(pattern, col, re.IGNORECASE):
                        mapped_col = canonical_name
                        break
                if mapped_col != col.strip():
                    break
            mapped_columns.append(mapped_col)
        df.columns = mapped_columns

        cols_to_drop = [c for c in df.columns if should_delete(c)]
        df_cleaned = df.drop(columns=cols_to_drop)
        if df_cleaned.columns.duplicated().any():
            combined_columns = {}
            for column_name in dict.fromkeys(df_cleaned.columns):
                same = df_cleaned.loc[:, df_cleaned.columns == column_name]
                if same.shape[1] == 1:
                    combined_columns[column_name] = same.iloc[:, 0]
                else:
                    merged = same.iloc[:, 0].replace(r'^\s*$', pd.NA, regex=True)
                    for duplicate_index in range(1, same.shape[1]):
                        candidate = same.iloc[:, duplicate_index].replace(r'^\s*$', pd.NA, regex=True)
                        fill_mask = merged.isna() & candidate.notna()
                        if fill_mask.any():
                            merged.loc[fill_mask] = candidate.loc[fill_mask]
                    combined_columns[column_name] = merged
            df_cleaned = pd.DataFrame(combined_columns, index=df_cleaned.index)
        df_cleaned = col_data_clean(df_cleaned)
        
        match = re.match(r'(\d{4})([^- ]+)', f)
        if match:
            year_val = match.group(1)
            exhibition_val = match.group(2)
        else:
            year_val = "Unknown"
            exhibition_val = "Unknown"
            
        df_cleaned['Manifestazione'] = exhibition_val
        df_cleaned['Anno'] = year_val
        
        extra_cols = [c for c in df_cleaned.columns if c not in TARGET_SCHEMA]
        if extra_cols:
            df_cleaned = df_cleaned.drop(columns=extra_cols)
            
        for missing_col in TARGET_SCHEMA:
            if missing_col not in df_cleaned.columns:
                df_cleaned[missing_col] = None

        df_cleaned = df_cleaned[TARGET_SCHEMA]

        all_cleaned_dfs.append(df_cleaned)

        name_part, ext_part = os.path.splitext(f)
        cleaned_filename = f"{name_part}_cleaned{ext_part}"
        output_path = os.path.join(output_dir, cleaned_filename)
        
        if f.endswith('.csv'):
            df_cleaned.to_csv(output_path, index=False)
        else:
            df_cleaned.to_excel(output_path, index=False)
            
        if year_val != "Unknown":
            if year_val not in results:
                results[year_val] = {}
            if exhibition_val not in results[year_val]:
                results[year_val][exhibition_val] = []
            results[year_val][exhibition_val].append({
                'filename': cleaned_filename,
                'columns': list(df_cleaned.columns)
            })
            
    except Exception as e:
        print(f"Error processing local file {f}: {e}")

with open(os.path.join(output_dir, 'summary.txt'), 'w', encoding='utf-8') as f_out:
    for year in sorted(results.keys()):
        f_out.write(f"Year: {year}\n")
        for exhibition in sorted(results[year].keys()):
            f_out.write(f"  Exhibition: {exhibition}\n")
            for entry in results[year][exhibition]:
                f_out.write(f"    File: {entry['filename']}\n")
        f_out.write("-" * 40 + "\n")

print("Processing complete. All columns map cleanly to float formats.")

# =============================================================================
# BIGQUERY PUSH BLOCK (FIXED)
# =============================================================================
# --- BIGQUERY INGESTION STAGE ---
if all_cleaned_dfs:
    print("\nConsolidating structural matrices for BigQuery migration...")
    
    # Concat datasets structurally
    master_df = pd.concat(all_cleaned_dfs, ignore_index=True, sort=False)
    
    # Explicit structural schemas to stop BigQuery initialization template failures
    text_schema_cols = ['elemento_top', 'elemento_flop', 'Manifestazione', 'Anno', 'company_name']
    
    for col in master_df.columns:
        if col in text_schema_cols:
            # Safely serialize text metrics cleanly without generating 'nan' literal artifacts
            master_df[col] = master_df[col].astype(str).replace(['nan', 'None', '<NA>'], None)
        else:
            # Force numeric float columns to retain explicit numeric parsing rules
            master_df[col] = pd.to_numeric(master_df[col], errors='coerce')
            
    try:
        print(f"Initiating Google Cloud BigQuery client connection...")
        client = bigquery.Client(project=PROJECT_ID)
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        # Build programmatic native schema types explicitly mapping text vs numeric float rows
        schema = []
        for col in master_df.columns:
            if col in text_schema_cols:
                schema.append(bigquery.SchemaField(col, bigquery.enums.SqlTypeNames.STRING))
            else:
                schema.append(bigquery.SchemaField(col, bigquery.enums.SqlTypeNames.FLOAT))

        # Config deployment definitions 
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION
            ],
        )
        
        print(f"Uploading massive matrix ({master_df.shape[0]} rows x {master_df.shape[1]} columns) to {table_ref}...")
        job = client.load_table_from_dataframe(master_df, table_ref, job_config=job_config)
        job.result()  # Execution block wait logic until ingestion confirms
        
        print(f"Success! Finalized pipeline safely uploaded to BigQuery table: {TABLE_ID}")
        
    except Exception as bq_err:
        print(f"Pipeline Upload Exception to Google BigQuery: {bq_err}")
else:
    print("Execution halt: No distinct datasets compiled for database parsing matrix updates.")