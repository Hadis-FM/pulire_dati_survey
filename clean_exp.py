import os
import pandas as pd
import re
from google.cloud import bigquery

# Configuration
input_dir = '.'
output_dir = 'cleaned_reports'

PROJECT_ID = "data-test-389108"
DATASET_ID = "survey_mostre"
TABLE_ID = "master_survey_23_present_test_v1"


TARGET_SCHEMA = [
    'soddisfazione_complessiva',
    'net_promoter_commercio',
    'elemento_top',
    'elemento_flop',
    'importanza_evento',  # Kept mapping name alignment below
    'possibilita_di_ritorno',
    'importanza_aspetti_quantita_di_visitatori',
    'importanza_aspetti_qualita_dei_visitatori',
    'importanza_aspetti_appearance_of_the_fair',
    'importanza_aspetti_internazionalita_dei_visitatori',
    'importanza_aspetti_rappresentativita_del_settore',
    'soddisfazione_aspetti_quantita_di_visitatori',
    'soddisfazione_aspetti_qualita_dei_visitatori',
    'soddisfazione_aspetti_appearance_of_the_fair',
    'soddisfazione_aspetti_internazionalita_dei_visitatori',
    'soddisfazione_aspetti_rappresentativita_del_settore',
    'Manifestazione',
    'Anno',
    'importanza_aspetti_immagine_complessiva_della_fiera',
    'soddisfazione_aspetti_immagine_complessiva_della_fiera',
    'importanza_aspetti_quantity_of_collectors',
    'importanza_aspetti_quality_of_collectors',
    'importanza_aspetti_internationality_of_collectors',
    'importanza_aspetti_exhibition_layout_and_sections',
    'importanza_aspetti_quality_of_artworks',
    'soddisfazione_aspetti_quantity_of_collectors',
    'soddisfazione_aspetti_quality_of_collectors',
    'soddisfazione_aspetti_exhibition_layout_and_sections',
    'soddisfazione_aspetti_quality_of_artworks',
    'importanza_aspetti_business_development',
    'soddisfazione_aspetti_business_development',
    'importanza_aspetti_innovazione_di_prodotto',
    'soddisfazione_aspetti_innovazione_di_prodotto',
    'importanza_aspetti_programma_convegnistico',
    'soddisfazione_aspetti_programma_convegnistico',
    'sostenibilità_allestimenti_in_materiali_riutilizzabili',
    'sostenibilità_illuminazione_a_led',
    'sostenibilità_ristorazione_plastic_free',
    'sostenibilità_presenza_di_espositori_che_propongono_prodotti_e_soluzioni_sostenibili',
    'sostenibilità_Organizzazione_di_conferenze_su_tematiche_relative_alla_sostenibilità',
    'aspetti_assistenza_commerciale_e_amministrativa',
    'aspetti_ristorazione_bar',
    'aspetti_logistica_di_quartiere_segnaletica_indicazioni_per_orientarsi',
    'aspetti_pulizia',
    'aspetti_parcheggi',
    'aspetti_misure_di_sicurezza',
    'aspetti_servizio_di_allestimento_stand',
    'servizi_digitali_catalogo_digital_platform',
    'servizi_digitali_fiera_id',
    'servizi_digitali_portale_espositori',
    'servizi_digitali_sistema_inviti_clientela',
    'servizi_digitali_app_manifestazione_lead_scanner',
    'soddisfazione_digital_platform_facilita_uso',
    'soddisfazione_digital_platform_pianificazione_pre_fiera',
    'soddisfazione_digital_platform_acquisizione_contatti_lead_scanner',
    'soddisfazione_digital_platform_profilo_buyer_incontrati',
    'soddisfazione_digital_platform_stand_virtuale',
    'soddisfazione_digital_platform_appuntamenti_buyer',
    'soddisfazione_digital_platform_paesi_buyer_incontrati',
    'soddisfazione_digital_platform_qualita_buyer_incontrati',
    'company_name'
]


# Flexible keywords to catch columns regardless of trailing spaces
to_delete_patterns = [
    r'ID',                        # Matches ID, surveyDataId, Fiera ID etc.
    r'STARTDATE',
    r'STARTTIME',
    r'COMPLETEDDATE',
    r'COMPLETEDTIME',
    r'LANGCODE',
    r'COMPLETIONSTATUS',
    r'SURVEYDATAID',
    r'MyMatching',
    r'Canali',
    r'jobTitle',
    r'Privacy',
    r'Altre fiere',
    r'Competitors',
    
    # --- UNCOMMON COLUMNS PATH PATTERNS (2023 - 2024 Manifestations) ---
    r'Tipologia di visitatore di interesse',                             # Unique to 2023GEE [cite: 7]
    r'Soddisfazione per incontro con target di interesse',              # Unique to 2023GEE/2023MADE [cite: 7, 20]
    r'Altro evento MIBA visitato',                                      # Unique to 2023GEE [cite: 11]
    r'Mese dell\'anno',                                                 # Unique to 2023GEE [cite: 11]
    r'Interesse per pubblico consumer',                                 # Unique to 2023GEE [cite: 11]
    r'Orari di apertura',                                               # Unique to 2023Host [cite: 15]
    r'Date Homi vs eventi moda',                                        # Unique to 2023MFJset [cite: 34]
    r'Valutazione convegni - Overall quality of the agenda',            # Unique to 2023MFJset [cite: 33]
    r'Valutazione convegni - Quality of the speeches',                  # Unique to 2023MFJset [cite: 34]
    r'Valutazione convegni - Variety of contents',                      # Unique to 2023MFJset [cite: 34]
    r'Ritorno HOMI',                                                    # Unique to 2023MH [cite: 37]
    r'Visitatore incontrato - Art advisor',                             # Unique to 2023Miart [cite: 42]
    r'Visitatore incontrato - Private collector',                       # Unique to 2023Miart [cite: 42]
    r'Visitatore incontrato - Representative of public institutions',   # Unique to 2023Miart [cite: 43]
    r'Visitatore incontrato - General public',                          # Unique to 2023Miart [cite: 43]
    r'Allestimenti - Customisations',                                   # Unique to 2023Miart [cite: 44]
    r'Allestimenti - Lightning',                                        # Unique to 2023Miart [cite: 44]
    r'Allestimenti - Overall booth appearance',                         # Unique to 2023Miart [cite: 44]
    r'Allestimenti - Setup',                                            # Unique to 2023Miart [cite: 44]
    r'Assistance from the unique sales team',                           # Unique to 2023PTE [cite: 48]
    r'Interesse per Cyber Security Arena',                              # Unique to 2023SICUREZZA
    r'Alternativa ANUGA SIAL',                                          # Unique to 2023TUTTOFOOD [cite: 68]
    r'Motivo alternativa',                                              # Unique to 2023TUTTOFOOD [cite: 68]
    r'Accordo date con White',                                          # Unique to 2024F&Jsett / 2024MFJfeb
    r'Spedimento padiglioni 14/18',                                     # Unique to 2024F&Jsett
    r'Padiglione preferito',                                            # Unique to 2024F&Jsett
    r'Contemporaneità con Homi Fashion & Jewels',                       # Unique to 2024MFJfeb
    r'Layout padiglione unico',                                         # Unique to 2024MFJfeb
    r'Numero edizioni a cui ha partecipato',                            # Unique to 2024MH Breakdown Manifestations
    r'Frequenza di partecipazione a Milano Home',                       # Unique to 2024MH
    r'Grado di internazionalizzazione dell\'offerta',                  # Unique to 2024MH
    r'Canali di vendita principali',                                    # Unique to 2024MH
    r'Tipologia di prodotti esposti',                                   # Unique to 2024MH
    r'Nuove aree tematiche introdotte',                                 # Unique to 2024MH
    r'Sezione della fiera in cui ha esposto',                           # Unique to 2024Miart
    r'Tipologia di collezionisti incontrati',                           # Unique to 2024Miart
    r'Soddisfazione per il livello delle vendite',                      # Unique to 2024Miart
    r'Valutazione del programma VIP',                                   # Unique to 2024Miart
    r'Sezioni espositive di maggiore interesse',                        # Unique to 2024NME
    r'Tipologia di visitatori qualificati incontrati',                  # Unique to 2024NME
    r'Giudizio sui convegni e workshop',                                # Unique to 2024NME
    r'Edizioni PTE',                                                    # Unique to 2024PTE
    r'Settore PTE',                                                     # Unique to 2024PTE
    r'Visitatore PTE',                                                  # Unique to 2024PTE
    r'Export PTE',                                                      # Unique to 2024PTE
    r'Canale PTE',                                                      # Unique to 2024PTE
    r'Prodotti PTE',                                                    # Unique to 2024PTE
    r'Nuova area macchine',                                             # Unique to 2024PTE
    r'Servizio matchmaking',                                            # Unique to 2024PTE
    r'Commento matchmaking',                                            # Unique to 2024PTE
    r'Edizioni QM',                                                     # Unique to 2024QM
    r'Settore QM',                                                      # Unique to 2024QM
    r'Visitatore QM',                                                   # Unique to 2024QM
    r'Export QM',                                                       # Unique to 2024QM
    r'Posizionamento QM',                                               # Unique to 2024QM
    r'Focus QM',                                                        # Unique to 2024QM
    r'Nuova area trend',                                                # Unique to 2024QM
    r'Sfilate collettive',                                              # Unique to 2024QM
    r'Commento sfilate',                                                # Unique to 2024QM
    r'Edizioni Sposa',                                                  # Unique to 2024Sposa
    r'Settore Sposa',                                                   # Unique to 2024Sposa
    r'Visitatore Sposa',                                                # Unique to 2024Sposa
    r'Export Sposa',                                                    # Unique to 2024Sposa
    r'Produzione Sposa',                                                # Unique to 2024Sposa
    r'Focus Sposa',                                                     # Unique to 2024Sposa
    r'Area Sposa Excellence',                                           # Unique to 2024Sposa
    r'Sfilate Si Sposaitalia',                                          # Unique to 2024Sposa
    r'Commento sfilate sposa',                                          # Unique to 2024Sposa
    r'Valutazione Transpotec Lab',                                      # Unique to 2024TL
    r'Interesse per area Move City Sport',                              # Unique to 2024TL
    r'Utilità del test drive veicoli',                                  # Unique to 2024TL
    r'Focus su sostenibilità e trazioni alternative',                  # Unique to 2024TL
    
    # --- UNCOMMON METRICS PATTERNS (2025 - 2026 Strategic Metrics) ---
    r'Utilità incontri prefissati \(MyMatching\)',                       # Unique to 2025BIT
    r'Suggerimenti per migliorare MyMatching',                          # Unique to 2025BIT
    r'Valutazione dell\'area "Village"',                                # Unique to 2025BIT
    r'Bringing Innovation Into Travel',                                 # Unique to 2025BIT
    r'suddivisione nelle macro-aree',                                   # Unique to 2025BIT
    r'Adeguatezza dei giorni di apertura',                              # Unique to 2025BIT
    r'Impatto della vicinanza con altri eventi',                        # Unique to 2025BIT
    r'Livello di digitalizzazione dei servizi',                         # Unique to 2025BIT
    r'Intenzione di espandere lo spazio espositivo',                    # Unique to 2025BIT
    r'HostMilano come hub globale',                                     # Unique to 2025Host
    r'Profilo internazionale dei buyer',                                # Unique to 2025Host
    r'Esplorare nuovi canali distributivi',                             # Unique to 2025Host
    r'Lanciare brevetti o innovazioni tecnologiche',                    # Unique to 2025Host
    r'Valutazione aree - Ristorazione Professionale',                   # Unique to 2025Host
    r'Valutazione aree - Bakery/Pizza/Pasta',                           # Unique to 2025Host
    r'Valutazione aree - Caffè/Te/Gelato/Pasticceria',                  # Unique to 2025Host
    r'Valutazione aree - Arredo/Tavola/Tecnologia',                     # Unique to 2025Host
    r'Efficacia degli eventi speciali',                                 # Unique to 2025Host
    r'Qualità del supporto logistico per merci voluminose',             # Unique to 2025Host
    r'Frequenza ideale dell\'evento',                                   # Unique to 2025Host
    r'Interesse per formati verticali/roadshow',                        # Unique to 2025Host
    r'Presenza e supporto del personale di assistenza',                 # Unique to 2025Host
    r'Livello di affollamento dei padiglioni',                          # Unique to 2025Host
    r'Interesse a partecipare a webinar preparatori',                   # Unique to 2025Host
    r'Utilizzo dell\'app ufficiale Fiera Milano',                       # Unique to 2025Host
    r'Gradimento del servizio Lounge/Aree Business',                    # Unique to 2025Host
    r'Percezione del brand HostMilano',                                 # Unique to 2025Host
    r'Valutazione sinergia MIBA',                                       # Unique to 2025MIBA
    r'Utilità del biglietto unico integrato',                           # Unique to 2025MIBA
    r'Rilevanza del target "Progettisti e Architetti"',                 # Unique to 2025MIBA
    r'Rilevanza del target "Imprese di costruzione"',                   # Unique to 2025MIBA
    r'Interesse per i percorsi tematici guidati intersalone',           # Unique to 2025MIBA
    r'Valutazione del layout integrato nei padiglioni',                 # Unique to 2025MIBA
    r'Efficacia dei talk e convegni congiunti \(MIBA Arena\)',          # Unique to 2025MIBA
    r'Formula integrata rispetto ai singoli saloni',                    # Unique to 2025MIBA
    r'Ottimizzazione dei tempi di visita grazie alla contemporaneità', # Unique to 2025MIBA
    r'Qualità del matching B2B cross-settoriale',                       # Unique to 2025MIBA
    r'Incremento di contatti non previsti da settori contigui',         # Unique to 2025MIBA
    r'Visibilità mediatica complessiva del polo MIBA',                  # Unique to 2025MIBA
    r'Chiarezza della comunicazione pre-fiera sulla formula',           # Unique to 2025MIBA
    r'Valutazione Salone del Franchising \(nuovo format\)',             # Unique to 2025SdF
    r'Efficacia dell\'area "Franchising Start"',                        # Unique to 2025SdF
    r'Qualità dei potenziali franchisee incontrati',                    # Unique to 2025SdF
    r'Interesse per i workshop su contrattualistica',                   # Unique to 2025SdF
    r'Utilità dello sportello di consulenza legale',                    # Unique to 2025SdF
    r'Rispondenza dei visitatori ai criteri di espansione',             # Unique to 2025SdF
    r'Efficacia dei pitch sul palco principale',                        # Unique to 2025SdF
    r'Utilità della Guida al Franchising distribuita',                  # Unique to 2025SdF
    r'Integrazione con servizi di finanziamento agevolato',             # Unique to 2025SdF
    r'Rinnovare la presenza per incrementare la rete',                  # Unique to 2025SdF
    r'Valutazione BIT 2026 \(nuovo posizionamento\)',                   # Unique to 2026BIT
    r'Efficacia dell\'area espositiva "Leisure Italy"',                 # Unique to 2026BIT
    r'Riscontro commerciale dall\'area "MICE & Wedding"',               # Unique to 2026BIT
    r'Qualità dei buyer internazionali selezionati dal programma Hosted',# Unique to 2026BIT
    r'Utilità dell\'estensione digitale della fiera nei giorni',        # Unique to 2026BIT
    r'Adeguatezza dei focus geografici',                                # Unique to 2026BIT
    r'Valutazione dei panel scientifici sulla sostenibilità',           # Unique to 2026BIT
    r'Efficacia delle iniziative di co-marketing territoriale',          # Unique to 2026BIT
    r'Ritorno sull\'investimento \(ROI\) stimato per i contatti',       # Unique to 2026BIT
    r'Valutazione Milano Home 2026 \(consolidamento brand\)',           # Unique to 2026MH
    r'Riscontro commerciale dall\'area "Green & Sustainable Living"',   # Unique to 2026MH
    r'Qualità dei dettaglianti e buyer indipendenti italiani',          # Unique to 2026MH
    r'Qualità dei buyer esteri introdotti tramite agenzie',             # Unique to 2026MH
    r'Utilità dei laboratori pratici e workshop sulle tecniche',        # Unique to 2026MH
    r'Efficacia delle aree di tendenza curate da designer',             # Unique to 2026MH
    r'Riscontro per il settore "Fragranze & Benessere Casa"',           # Unique to 2026MH
    r'Soddisfazione per il livello degli ordini diretti scritti',       # Unique to 2026MH
    r'Valutazione PTE 2026 \(focus personalizzazione tecnologica\)',    # Unique to 2026PTE
    r'Riscontro commerciale dall\'area "PTE Lab"',                      # Unique to 2026PTE
    r'Qualità e competenza dei professionisti della stampa',            # Unique to 2026PTE
    r'Qualità dei lead provenienti da agenzie di promozione',           # Unique to 2026PTE
    r'Interesse riscontrato per le soluzioni di packaging promozionale',# Unique to 2026PTE
    r'Gradimento dei seminari tecnici sulle nuove normative',           # Unique to 2026PTE
    r'Efficacia del tour guidato per i buyer nell\'area macchinari',    # Unique to 2026PTE
    r'Regalistica aziendale di alta gamma \(corporate gift\)',          # Unique to 2026PTE
    r'Valutazione QM 2026 \(evoluzione dell\'evento moda\)',            # Unique to 2026QM
    r'Efficacia dei Fashion Show collettivi per la visibilità',         # Unique to 2026QM
    r'Qualità e potere d\'acquisto dei buyer di boutique',              # Unique to 2026QM
    r'Qualità dei grandi buyer internazionali e department store',      # Unique to 2026QM
    r'Interesse riscontrato per le sezioni dedicate ai materiali',      # Unique to 2026QM
    r'Utilità delle conferenze sui trend macro-economici del settore',  # Unique to 2026QM
    r'Gradimento delle aree dedicate ai giovani designer emergenti',    # Unique to 2026QM
    # --- UNCOMMON METRICS PATTERNS (2025 - 2026 Strategic Metrics) ---
    r'Utilità incontri prefissati \(MyMatching\)',                       # Unique to 2025BIT
    r'Suggerimenti per migliorare MyMatching',                          # Unique to 2025BIT
    r'Valutazione dell\'area "Village"',                                # Unique to 2025BIT
    r'Bringing Innovation Into Travel',                                 # Unique to 2025BIT
    r'suddivisione nelle macro-aree',                                   # Unique to 2025BIT
    r'Adeguatezza dei giorni di apertura',                              # Unique to 2025BIT
    r'Impatto della vicinanza con altri eventi',                        # Unique to 2025BIT
    r'Livello di digitalizzazione dei servizi',                         # Unique to 2025BIT
    r'Intenzione di espandere lo spazio espositivo',                    # Unique to 2025BIT
    r'HostMilano come hub globale',                                     # Unique to 2025Host
    r'Profilo internazionale dei buyer',                                # Unique to 2025Host
    r'Esplorare nuovi canali distributivi',                             # Unique to 2025Host
    r'Lanciare brevetti o innovazioni tecnologiche',                    # Unique to 2025Host
    r'Valutazione aree - Ristorazione Professionale',                   # Unique to 2025Host
    r'Valutazione aree - Bakery/Pizza/Pasta',                           # Unique to 2025Host
    r'Valutazione aree - Caffè/Te/Gelato/Pasticceria',                  # Unique to 2025Host
    r'Valutazione aree - Arredo/Tavola/Tecnologia',                     # Unique to 2025Host
    r'Efficacia degli eventi speciali',                                 # Unique to 2025Host
    r'Qualità del supporto logistico per merci voluminose',             # Unique to 2025Host
    r'Frequenza ideale dell\'evento',                                   # Unique to 2025Host
    r'Interesse per formati verticali/roadshow',                        # Unique to 2025Host
    r'Presenza e supporto del personale di assistenza',                 # Unique to 2025Host
    r'Livello di affollamento dei padiglioni',                          # Unique to 2025Host
    r'Interesse a partecipare a webinar preparatori',                   # Unique to 2025Host
    r'Utilizzo dell\'app ufficiale Fiera Milano',                       # Unique to 2025Host
    r'Gradimento del servizio Lounge/Aree Business',                    # Unique to 2025Host
    r'Percezione del brand HostMilano',                                 # Unique to 2025Host
    r'Valutazione sinergia MIBA',                                       # Unique to 2025MIBA
    r'Utilità del biglietto unico integrato',                           # Unique to 2025MIBA
    r'Rilevanza del target "Progettisti e Architetti"',                 # Unique to 2025MIBA
    r'Rilevanza del target "Imprese di costruzione"',                   # Unique to 2025MIBA
    r'Interesse per i percorsi tematici guidati intersalone',           # Unique to 2025MIBA
    r'Valutazione del layout integrato nei padiglioni',                 # Unique to 2025MIBA
    r'Efficacia dei talk e convegni congiunti \(MIBA Arena\)',          # Unique to 2025MIBA
    r'Formula integrata rispetto ai singoli saloni',                    # Unique to 2025MIBA
    r'Ottimizzazione dei tempi di visita grazie alla contemporaneità', # Unique to 2025MIBA
    r'Qualità del matching B2B cross-settoriale',                       # Unique to 2025MIBA
    r'Incremento di contatti non previsti da settori contigui',         # Unique to 2025MIBA
    r'Visibilità mediatica complessiva del polo MIBA',                  # Unique to 2025MIBA
    r'Chiarezza della comunicazione pre-fiera sulla formula',           # Unique to 2025MIBA
    r'Valutazione Salone del Franchising \(nuovo format\)',             # Unique to 2025SdF
    r'Efficacia dell\'area "Franchising Start"',                        # Unique to 2025SdF
    r'Qualità dei potenziali franchisee incontrati',                    # Unique to 2025SdF
    r'Interesse per i workshop su contrattualistica',                   # Unique to 2025SdF
    r'Utilità dello sportello di consulenza legale',                    # Unique to 2025SdF
    r'Rispondenza dei visitatori ai criteri di espansione',             # Unique to 2025SdF
    r'Efficacia dei pitch sul palco principale',                        # Unique to 2025SdF
    r'Utilità della Guida al Franchising distribuita',                  # Unique to 2025SdF
    r'Integrazione con servizi di finanziamento agevolato',             # Unique to 2025SdF
    r'Rinnovare la presenza per incrementare la rete',                  # Unique to 2025SdF
    r'Valutazione BIT 2026 \(nuovo posizionamento\)',                   # Unique to 2026BIT
    r'Efficacia dell\'area espositiva "Leisure Italy"',                 # Unique to 2026BIT
    r'Riscontro commerciale dall\'area "MICE & Wedding"',               # Unique to 2026BIT
    r'Qualità dei buyer internazionali selezionati dal programma Hosted',# Unique to 2026BIT
    r'Utilità dell\'estensione digitale della fiera nei giorni',        # Unique to 2026BIT
    r'Adeguatezza dei focus geografici',                                # Unique to 2026BIT
    r'Valutazione dei panel scientifici sulla sostenibilità',           # Unique to 2026BIT
    r'Efficacia delle initiatives di co-marketing territoriale',          # Unique to 2026BIT
    r'Ritorno sull\'investimento \(ROI\) stimato per i contatti',       # Unique to 2026BIT
    r'Valutazione Milano Home 2026 \(consolidamento brand\)',           # Unique to 2026MH
    r'Riscontro commerciale dall\'area "Green & Sustainable Living"',   # Unique to 2026MH
    r'Qualità dei dettaglianti e buyer indipendenti italiani',          # Unique to 2026MH
    r'Qualità dei buyer esteri introdotti tramite agenzie',             # Unique to 2026MH
    r'Utilità dei laboratori pratici e workshop sulle tecniche',        # Unique to 2026MH
    r'Efficacia delle aree di tendenza curate da designer',             # Unique to 2026MH
    r'Riscontro per il settore "Fragranze & Benessere Casa"',           # Unique to 2026MH
    r'Soddisfazione per il livello degli ordini diretti scritti',       # Unique to 2026MH
    r'Valutazione PTE 2026 \(focus personalizzazione tecnologica\)',    # Unique to 2026PTE
    r'Riscontro commerciale dall\'area "PTE Lab"',                      # Unique to 2026PTE
    r'Qualità e competenza dei professionisti della stampa',            # Unique to 2026PTE
    r'Qualità dei lead provenienti da agenzie di promozione',           # Unique to 2026PTE
    r'Interesse riscontrato per le soluzioni di packaging promozionale',# Unique to 2026PTE
    r'Gradimento dei seminari tecnici sulle nuove normative',           # Unique to 2026PTE
    r'Efficacia del tour guidato per i buyer nell\'area macchinari',    # Unique to 2026PTE
    r'Regalistica aziendale di alta gamma \(corporate gift\)',          # Unique to 2026PTE
    r'Valutazione QM 2026 \(evoluzione dell\'evento moda\)',            # Unique to 2026QM
    r'Efficacia dei Fashion Show collettivi per la visibilità',         # Unique to 2026QM
    r'Qualità e potere d\'acquisto dei buyer di boutique',              # Unique to 2026QM
    r'Qualità dei grandi buyer internazionali e department store',      # Unique to 2026QM
    r'Interesse riscontrato per le sezioni dedicate ai materiali',      # Unique to 2026QM
    r'Utilità delle conferenze sui trend macro-economici del settore',  # Unique to 2026QM
    r'Gradimento delle aree dedicate ai giovani designer emergenti',    # Unique to 2026QM
    
    # --- MULTI-YEAR REPEATED PATTERNS (Requested Core Survey Fields) ---
    r'Obiettivi',                                                       # Present across multiple manifestation blocks [cite: 1, 6, 12, 18, 117]
    r'Obiettivi - Other - verbatim',                                    # Shared baseline text [cite: 6, 18]
    r'Raggiungimento obiettivi - To present new products',              # Key objective metric [cite: 1, 5, 12, 18, 117]
    r'Raggiungimento obiettivi - To meet my customers',                 # Naming cluster match [cite: 5, 12, 18]
    r'Raggiungimento obiettivi - To search for new prospects',          # Naming cluster match [cite: 5, 13, 18]
    r'Raggiungimento obiettivi - To develop negotiations and conclude orders', # Target milestone field [cite: 5, 13, 18]
    r'Raggiungimento obiettivi - Other',                                # General multi-year leftover field [cite: 5, 18]
    r'Eventi',                                                          # Matches 22. Eventi and general metrics [cite: 3, 39, 63, 84]
    r'Sabato',                                                          # Manifestation specific multi-year schedule [cite: 3, 63]
    r'Sabato - Other days - verbatim',                                  # Schedule fallback field [cite: 3, 63]
    r'Mercati abituali',                                                # Core commercial footprint tracking [cite: 3, 63]
    r'Mercati nuovi',                                                   # Target strategy metric [cite: 3, 63]
    r'Allestimento',                                                    # Matches setup, booths, and logistics sections [cite: 3, 34, 46, 63, 119]
    r'Allestimento val - Booth appearance',                             # Visual footprint indicator [cite: 3, 34, 63, 119]
    r'Allestimento val - Setting up and un-setting up',                 # Temporal field tracking operational performance [cite: 3, 34, 63, 119]
    r'Promozione - Social Media',                                       # Multi-manifestation promotion tracking [cite: 3, 27, 31, 63]
    r'Promozione - Newsletter',                                         # Core communication efficacy channel [cite: 3, 27, 31, 63]
    r'Promozione - Event website',                                      # Primary entry footprint hub tracker [cite: 3, 27, 31, 63]
    r'Promozione - Advertisement on industry sites',                     # Strategic B2B visibility placement [cite: 3, 27, 31, 64]
    r'Servizi 1 - Assistance from the sales team',                      # Basic CRM satisfaction parameter [cite: 4, 27, 31, 35, 64]
    r'Servizi 1 - Technical services support \(customer care\)',        # Help desk metric tracking [cite: 4, 35, 64]
    r'Servizi 1 - Administrative services support',                     # Standard financial/contract desk feedback [cite: 4, 27, 31, 35, 64]
    r'Servizi 1 - Assistance with technical set-up services',           # Operational support evaluation metric [cite: 4, 35, 64]
    r'Servizi 1 - Portal support \(E-service, E-commerce for exhibitors\)', # Digital backend usability [cite: 4, 35, 64]
    r'Servizi 2 - Timing of exhibit space allocation',                  # Early lifecycle milestone timing indicator [cite: 4, 35, 40, 64]
    r'Servizi 2 - Venue logistics/signage/directions for orientation',  # Quarter exploration tracking parameter [cite: 4, 35, 41, 64]
    r'Servizi 2 - Parking lots',                                        # Strategic quarter accessibility metric [cite: 4, 35, 41, 64]
    r'Servizi 2 - Catering',                                            # Food and hospitality evaluation baseline [cite: 4, 35, 41, 64]
    r'Servizi 2 - Cleaning',                                            # Essential facility standard evaluation metric [cite: 4, 35, 41, 64]
    r'Servizi 2 - Security measures',                                   # Safety enforcement auditing parameters [cite: 4, 5, 36, 41, 65]
    r'Servizi 3 - E-service / E-commerce Portal for Exhibitors',        # Core system interface portal metric [cite: 5, 41, 65]
    r'Servizi 3 - Option language value not found for en_GB',           # Naming layout error identifier string [cite: 5, 65]
    r'Servizi 3 - Digital catalog',                                     # Shared multi-year catalog metric [cite: 5, 65]
    r'Servizi aperta',                                                   # Free text open input tracker field [cite: 5, 41, 65]
    # --- GLOBAL ERA DELETION PATTERNS (Deletes items starting with these phrases across all years) ---
    r'^.*Servizi',                        # Matches "Servizi aperta", "23. Servizi 1...", etc.
    r'^.*Aggiornamenti sul settore',      # Matches any text or multi-year column starting here
    r'^.*Ordini',                         # Matches "11. Ordini", "9. Ordini", etc.
    r'^.*Channel evaluation',             # Matches "35. Channel evaluation..." lines
    r'^.*Sustainability',                 # Matches "28. Sustainability..." lines
    r'^.*Storico visita',                 # Matches "015. 21. Storico visita" or variations
    r'^.*Confronto HOMI Gennaio',         # Matches "016. 22. Confronto HOMI Gennaio" 
    r'^.*Perché confronto',               # Matches "017. 23. Perché confronto"
    r'^.*miart digital',                  # Matches any index layout variations of miart digital
    r'^.*Tipologia di pubblico',          # Matches any numeric prefixed public type breakdown
    r'^.*Social utilizzati'               # Matches any leading prefix for regular social use logs
    r'^.*Soddisfazione profili',

# --- ADDED FROM RAW TXT REPORT ANALYSIS (Useless metadata, demographics, operational, and channel logs) ---
    r'^surveyDataType$',
    r'^source$',
    r'^status$',
    r'^browserType$',
    r'^deviceType$',
    r'^userAgent$',
    r'^Unnamed: 10$',
    r'^salutation$',
    r'^firstName$',
    r'^lastName$',
    r'^emailAddress$',
    r'^Ruolo in azienda:.*$',
    r'^Consenso$',
    r'^Age$',
    r'^Età$',
    r'^Nazione$',
    r'^Paese$',
    r'^Provenienza$',
    r'^Country$',
    r'^Settore$',
    r'^Categoria$',
    r'^Macrocategoria$',
    r'^attività$',
    r'^Azienda$',
    r'^Storico$',
    r'^Superficie$',
    r'^Superficie stand$',
    r'^MQ$',
    r'^Stand$',
    r'^Padiglione$',
    r'^HALL$',
    r'^Hall$',
    r'^Sezione$',
    r'^Tipologia$',
    r'^Giorni di manifestazione$',
    r'^.*\. Durata$',
    r'^.*\. Durata - .*$',
    r'^.*\. Data$',
    r'^.*\. Altro mese$',
    r'^.*\. Cadenza$',
    r'^.*\. Date$',
    r'^.*\. Date - .*$',
    r'^.*\. Scelta data$',
    r'^.*\. Data preferita$',
    r'^.*\. Giorni$',
    r'^.*\. Giorni - .*$',
    r'^.*\. Periodo$',
    r'^.*\. Annuale e biennale$',
    r'^.*\. Frequenza$',
    r'^.*\. Luogo$',
    r'^.*\. Promozione - Social network$',
    r'^.*\. Promozione - Social Network$',
    r'^.*\. Promozione - Advertising on industry sites$',
    r'^.*\. Promozione - Sito web dell\'evento$',
    r'^.*\. Promozione - Pubblicità su riviste/siti di settore$',
    r'^.*\. Promozione - Pubblicità su siti di settore$',
    r'^.*\. Promozione - Option language value not found for en_GB.*$',
    r'^Social media utilizzati regolarmente$',
    r'^.*\. Social fiera$',
    r'^.*\. Social fiera - .*$',
    r'^.*\. Social utilizzati$',
    r'^.*\. Social utilizzati - .*$',
    r'^.*\. Event channels$',
    r'^.*\. Event channels - .*$',
    r'^.*\. Event social$',
    r'^.*\. Event social - .*$',
    r'^.*\. Use of event channels$',
    r'^.*\. Used channels$',
    r'^Fatturato atteso$',
    r'^.*\. n\. contatti$',
    r'^Contatti$',
    r'^.*\. Contatti generati$',
    r'^.*\. valore vendite 12ME$',
    r'^.*\. Conclusione trattative$',
    r'^.*\. ROI$',
    r'^Partecipazione a convegni$',
    r'^Valutazione convegni - .*$',
    r'^Differenze competitor$',
    r'^Valutazione Competitor:.*$',
    r'^.*\. Interesse visitatori$',
    r'^.*\. Visitatore incontrato - .*$',
    r'^.*\. Piattaforma utile$',
    r'^Allestimenti - .*$',
    r'^.*\. Allestimenti - .*$',
    r'^.*\. Info fiera$',
    r'^.*\. Iniziative fiera - .*$',
    r'^Altri brand$',
    r'^.*\. Visitatori di interesse$',
    r'^.*\. Visitatori di interesse - .*$',
    r'^.*\. Aggiornamenti$',
    r'^.*\. Aggiornamenti - .*$',
    r'^.*\. Altri settori$',
    r'^.*\. Tipologie di pubblico$',
    r'^.*\. Brand Ambassador$',
    r'^.*\. Soddisfazione Brand Ambassador$',
    r'^.*\. Conoscenza Transpotec$',
    r'^.*\. Sinergie Transpotec$',
    r'^.*\. Influenza Milano$',
    r'^.*\. Milano punto forza$',
    r'^.*\. Conoscenza NME$',
    r'^.*\. Sinergie NME$',
    r'^.*\. Visitatore di interesse$',
    r'^.*\. Visitatore di interesse - .*$',
    r'^.*\. Influence in the sector$',
    r'^.*\. Profilo visitatori$',
    r'^.*\. Profilo visitatori - .*$',
    r'^.*\.Distintività$',
    r'^.*\.Layout$',
    r'^.*\. Valutazione nuovo layout$',
    r'^.*\.Esperienza overall$',
    r'^Percezione del brand$',
    r'^Paese target$',
    r'^Evento$',
    r'^.*\. Valutazione complessiva$',
    r'^Testimonianza$',
    r'^Influenza$',
    r'^Influenza2$',
    r'^.*\. Influenza settore$',
    r'^DP$',
    r'^profili di visitatori.*$',
    r'^profili di visitator.*$',
    r'^42. Soddisfazione visitatori*$',
    r'^mercati di interesse - .*$',
    r'^Visitatori per il futuro$',
    r'^Countries for the future \d$',
    r'^Countries for the future \d - .*$',
    r'^Nazioni per il futuro \d$',
    r'^.*\. Soddisfazione pubblico - .*$',
    r'^Profili -.*$',
    r'^contatti.*$',
    r'^competitor.*$',
    r'^43. Regioni.*$',
    r'^New Profile.*$',
    r'^Valutazione Competitor.*$',
    r'^città,.*$',
    r'^SQM.*$',
    r'^94. Commenti finali.*$',
    r'^42. Soddisfazione visitatori.*$',
    r'^Soddisfazione visitatori.*$',
    r'^11.Soddisfazione profili.*$',
    r'^44. Soddisfazione regioni.*$',
    r'^27. Meet&amp;Coffee.*$',
    r'^45. Padiglioni.*$',
    r'^Social media utilizzati regolarmente.*$',
    r'^Indice espositori.*$',
    r'^92. Commenti.*$',
    r'^Commenti.*$',
    r'^Conclusione trattative.*$',
    r'^Perché?.1.*$',
    r'^Perché?.*$',
    r'^17. Luogo .*$',
    r'^Paese DB.*$',
    r'^Storico DB.*$',
    r'^Hall DB.*$',
    r'^06. Soddisfazione aspetti - Copertura media e social dell’evento.*$',
    r'^10. Soddisfazione visitatori - Franchisor.*$',
    r'^10. Soddisfazione visitatori - Franchisee.*$',
    r'^10. Soddisfazione visitatori - Visitatore generico.*$',
    r'^10. Soddisfazione visitatori - Altro.*$',
    r'^10. Soddisfazione visitatori : Altro - other verbatim.*$',
    r'^12. Valutazione complessiva.*$',
    r'^10. Soddisfazione visitatori - Altro.*$',
    r'^10. Soddisfazione visitatori - Altro.*$',
    r'^Punti di forza.*$',
    r'^Miglioramenti.*$',
    r'^Altri aspetti - copy - Presence of end consumers.*$',
    r'^Altri aspetti - Presence of end consumers.*$',
    r'^07. Importanza aspetti - Conferences and seminars featured.*$',
    r'^08. Soddisfazione aspetti - Conferences and seminars featured.*$',
    r'^7. Importanza aspetti - Events or conferences.*$',
    r'^8. Sodd aspetti - Events or conferences.*$',
    r'^05. Importanza aspetti - Copertura media e social dell’evento.*$',
    r'^DP: NO, Perchè\? - other verbatim.*$',
    # --- ADDED TO CATCH 2026 EDGE CASES & UNWANTED KPIS ---
    r'^ruolo azienda.*',
    r'^perchè no.*',
    r'^durata alternativa.*',
    r'^concomitanza.*',
    r'^funzionalita DP.*',
    r'^città, regione o Paese.*'

]


# --- NEW COLUMN MAPPING FEATURE ---

column_mappings = {
    'possibilita_di_ritorno': [
        r'Probabilita_di_ritorno',
        r'^Ritorno$',
        r'Probabilità di ritorno',
        r'Likelihood of return - LoR',
        r'Probabilità di ritorno (evento annuale)',
        r'6. Ritorno',
        r'06. Probabilità di ritorno'
    ],
    'net_promoter_commercio': [
        r'Net promoter \(commercio\)',                  
        r'Net Promoter Score - NPS \(trade\)',          
        r'0?2\. Net promoter \(commercio\)'     # Updated to catch "02." and "2." 
    ],
    'importanza_evento': [
        r'3. Importanza evento',
        r'Importanza dell\'evento',
        r'03. Importanza evento',
        r'Importance of event',
        r'Importanza di - eventName',
        r'01. Importanza evento',
        r'1. Importanza complessiva'
    ],
    'company_name': [
        r'companyName',
        r'Company Name',
        r'Company name',
        r'Nome azienda'
    ],
    'soddisfazione_complessiva': [
        r'1. Soddisfazione complessiva',
        r'Overall satisfaction',
        r'01. Soddisfazione complessiva',
        r'Soddisfazione complessiva',
        r'02. Soddisfazione complessiva'
    ],
    'importanza_aspetti_quantita_di_visitatori':[
        r'7. Importanza aspetti - Quantity of visitors',
        r'07. Importanza aspetti - Number of visitors',
        r'Importanza aspetti - Numero dei visitatori',
        r'05. Importanza aspetti - Numero dei visitatori',
        r'07. Importanza aspetti - Quantità di visitatori',
        r'Altri aspetti - copy - Quantity of visitors',
        r'Altri aspetti - copy - Number of visitors',
        r'07. Importanza aspetti - Numero di visitatori'
    ],
    'importanza_aspetti_qualita_dei_visitatori': [
        r'^07\. Importanza aspetti - Qualità dei visitatori$',
        r'^7\. Importanza aspetti - Qualità dei visitatori$',
        r'^Importanza aspetti - Qualità dei visitatori$',
        r'^05\. Importanza aspetti - Qualità di visitatori$',
        r'^7\. Importanza aspetti - Quality of visitors$',
        r'^07\. Importanza aspetti - Quality of visitors$',
        r'^Altri aspetti - copy - Quality of visitors$',
    ],
    'importanza_aspetti_internazionalita_dei_visitatori': [
        r'^07\. Importanza aspetti - Internazionalità dei visitatori$',
        r'^7\. Importanza aspetti - Internazionalità dei visitatori$',
        r'^Importanza aspetti - Internazionalità dei visitatori$',
        r'^7\. Importanza aspetti - International nature of visitors$',
        r'^07\. Importanza aspetti - Internationality of visitors$',
        r'^Altri aspetti - copy - Internationality of visitors$',
        r'^Altri aspetti - copy - Presence of international visitors$',
    ],
    'importanza_aspetti_immagine_complessiva_della_fiera': [
        r'^07\. Importanza aspetti - Immagine complessiva della fiera$',
        r'^7\. Importanza aspetti - Immagine complessiva della fiera$',
        r'^Importanza aspetti - Immagine complessiva della fiera$',
        r'^05\. Importanza aspetti - Immagine compleassiva della fiera$',
        r'^7\. Importanza aspetti - Overall image of the fair$',
        r'^07\. Importanza aspetti - Overall image of the trade show$',
        r'^Altri aspetti - copy - Overall look of the exhibition$',
        r'^Altri aspetti - copy - Overall image of the trade show$'
        r'^7. Importanza aspetti - Overall image of the exhibition$',
        r'^7. Importanza aspetti - Overall image of the exhibition$',
        r'^Altri aspetti - copy - Overall image of the trade show$'

    ],
    'importanza_aspetti_appearance_of_the_fair': [
        r'^07\. Importanza aspetti - Appearance of the exhibition \(common areas, layouts, etc\.\)$',
        r'^Altri aspetti - copy - Appearance of the exhibition \(common areas, layouts, etc\.\)$'

    ],
    'importanza_aspetti_rappresentativita_del_settore': [
        r'^07\. Importanza aspetti - Rappresentatività del settore$',
        r'^7\. Importanza aspetti - Rappresentatività del settore$',
        r'^Importanza aspetti - Rappresentatività del settore$',
        r'^05\. Importanza aspetti - Rappresentatività del settore$',
        r'^7\. Importanza aspetti - Representation of the industry$',
        r'^07\. Importanza aspetti - Representativeness of the industry$',
        r'^Altri aspetti - copy - Representativeness of the sector$',
        r'^Altri aspetti - copy - Coverage of the sector$',
        r'^Altri aspetti - copy - Representativeness of the galleries$',
        r'^07. Importanza aspetti - Representativeness of the sector$'
    ],
    'importanza_aspetti_innovazione_di_prodotto': [
        r'^07\. Importanza aspetti - Innovazione di prodotto$',
        r'^7\. Importanza aspetti - Innovazione di prodotto$',
        r'^Importanza aspetti - Innovazione di prodotto$',
        r'^07\. Importanza aspetti - Product innovation$',
        r'^7\. Importanza aspetti - Product innovation$',
        r'^Importanza aspetti - Product innovation$',
        r'^Altri aspetti - copy - Product innovation$'
    ],
    'soddisfazione_aspetti_quantita_di_visitatori': [
        r'^08\. Soddisfazione aspetti - Quantità di visitatori$',
        r'^08\. Soddisfazione aspetti - Numero di visitatori$',
        r'^06\. Soddisfazione aspetti - Numero dei visitatori$',
        r'^8\. Sodd aspetti - Quantity of visitors$',
        r'^08\. Soddisfazione aspetti - Number of visitors$',
        r'^Altri aspetti - Number of visitors$',
        r'^Altri aspetti - Quantity of visitors$',
        r'08. Soddisfazione aspetti - Quantity of visitors'
    ],
    'soddisfazione_aspetti_internazionalita_dei_visitatori': [
        r'^08\. Soddisfazione aspetti - Internazionalità dei visitatori$',
        r'^8\. Sodd aspetti - International nature of visitors$',
        r'^08\. Soddisfazione aspetti - Internationality of visitors$',
        r'^Altri aspetti - Internationality of visitors$',
        r'^Altri aspetti - Presence of international visitors$',
        r'^Altri aspetti - Internationality of collectors$'
    ],
    'soddisfazione_aspetti_qualita_dei_visitatori': [
        r'^08\. Soddisfazione aspetti - Qualità dei visitatori$',
        r'^06\. Soddisfazione aspetti - Qualità di visitatori$',
        r'^8\. Sodd aspetti - Quality of visitors$',
        r'^08\. Soddisfazione aspetti - Quality of visitors$',
        r'^Altri aspetti - Quality of visitors$',
    ],
    'soddisfazione_aspetti_immagine_complessiva_della_fiera': [
        r'^08\. Soddisfazione aspetti - Immagine complessiva della fiera$',
        r'^06\. Soddisfazione aspetti - Immagine compleassiva della fiera$',
        r'^8\. Sodd aspetti - Overall image of the fair$',
        r'^08\. Soddisfazione aspetti - Overall image of the trade show$',
        r'^08\. Soddisfazione aspetti - Overall image of the exhibition$',
        r'^Altri aspetti - Overall look of the exhibition$',
        r'^8. Sodd aspetti - Overall image of the exhibition$',
        r'^Altri aspetti - Overall image of the trade show$'
    ],
    'soddisfazione_aspetti_appearance_of_the_fair': [
        r'^Altri aspetti - Appearance of the fair \(common areas, layouts, etc\.\)$',
        r'08. Soddisfazione aspetti - Appearance of the fair (common areas, layouts, etc.)',
        r'^08. Soddisfazione aspetti - Appearance of the fair \(common areas, layouts, etc\.\)$'
    ],
    'soddisfazione_aspetti_rappresentativita_del_settore': [
        r'^08\. Soddisfazione aspetti - Rappresentatività del settore$',
        r'^06\. Soddisfazione aspetti - Rappresentatività del settore$',
        r'^8\. Sodd aspetti - Representation of the industry$',
        r'^08\. Soddisfazione aspetti - Representativeness of the industry$',
        r'^08\. Soddisfazione aspetti - Representativeness of the sector$',
        r'^Altri aspetti - Representativeness of the sector$',
        r'^Altri aspetti - Coverage of the sector$',
        r'^Altri aspetti - Representativeness of the galleries$'
    ],
    'soddisfazione_aspetti_innovazione_di_prodotto': [
        r'^08\. Soddisfazione aspetti - Innovazione di prodotto$',
        r'^08\. Soddisfazione aspetti - Product innovation$',
        r'^8\. Sodd aspetti - Product innovation$',
        r'^Altri aspetti - Product innovation$'
    ],
    "elemento_top": [
        r"^Elemento top$",
        r"^Net promoter verbatim$",  # Strict match: will ignore the copy
        r"^91. Elemento top$"
    ],
    "elemento_flop": [
        r"^Elemento flop$",
        r"^Net promoter verbatim - copy$",  # Strict match for the copy
        r"^92. Elemento flop$"
    ],
    'importanza_aspetti_quantity_of_collectors': [
        r'^Altri aspetti - copy - Quantity of collectors$'
    ],
    'soddisfazione_aspetti_quantity_of_collectors': [
        r'^Altri aspetti - Quantity of collectors$'
    ],
    'importanza_aspetti_quality_of_collectors': [
        r'^Altri aspetti - copy - Quality of collectors$'
    ],
    'soddisfazione_aspetti_quality_of_collectors': [
        r'^Altri aspetti - Quality of collectors$'
    ],
    'importanza_aspetti_internationality_of_collectors': [
        r'^Altri aspetti - copy - Internationality of collectors$'
    ],
    'soddisfazione_aspetti_internationality_of_collectors': [
        r'^Altri aspetti - Internationality of collectors$'
    ],
    'importanza_aspetti_exhibition_layout_and_sections': [
        r'^Altri aspetti - copy - Exhibition layout and sections$'
    ],
    'soddisfazione_aspetti_exhibition_layout_and_sections': [
        r'^Altri aspetti - Exhibition layout and sections$'
    ],
    'importanza_aspetti_quality_of_artworks': [
        r'^Altri aspetti - copy - Quality of artworks$'
    ],
    'soddisfazione_aspetti_quality_of_artworks': [
        r'^Altri aspetti - Quality of artworks$'
    ],
    'importanza_aspetti_business_development': [
        r'^Altri aspetti - copy - Business development$'
    ],
    'soddisfazione_aspetti_business_development': [
        r'^Altri aspetti - Business development$'
    ],
    'importanza_aspetti_programma_convegnistico': [
        r'^0?7\. Importanza aspetti - Programma convegnistico$',
        r'^Importanza aspetti - Programma convegnistico$'
    ],
    'soddisfazione_aspetti_programma_convegnistico': [
        r'^0?8\. Soddisfazione aspetti - Programma convegnistico$',
        r'^8\. Sodd aspetti - Programma convegnistico$'
    ],

    'sostenibilità_allestimenti_in_materiali_riutilizzabili': [
        r'riutilizzab|reusable.*materials'
    ],

    'sostenibilità_illuminazione_a_led': [
        r'(illuminazione.*led|led.*lighting|led lighting|led)'
    ],

    'sostenibilità_ristorazione_plastic_free': [
        r'(plastic[\s\-"”]*free|ristorazione.*plastic)'
    ],

    'sostenibilità_presenza_di_espositori_che_propongono_prodotti_e_soluzioni_sostenibili': [
        r'((espositori|exhibitors).*(sostenibil|sustainab))'
    ],

    'sostenibilità_organizzazione_di_conferenze_su_tematiche_relative_alla_sostenibilità': [
        r'((conferenze|conference).*(sostenibil|sustainab))'
    ],
    # ========================================================
    # SERVIZI DIGITALI E DIGITAL PLATFORM - ESPOSITORI 2023-2026
    # ========================================================
    'servizi_digitali_catalogo_digital_platform': [
        r'^(?:19\. Soddisfazione servizi digitali|(?:23|24)\. Servizi digitali|Servizi digitali|25\. Servizi 3) - (?:Catalogo Digitale|Catalogo digitale(?: \(Digital Platform\))?|Catalogo digitale \/ App|Digital Platform|Digital catalog|Digital catalogue|copy - copy - Digital catalogue)$'
    ],
    'servizi_digitali_fiera_id': [
        r'^(?:24\. Servizi digitali|Servizi digitali) - Utilizzo e accesso con Fiera ID$'
    ],
    'servizi_digitali_portale_espositori': [
        r'^(?:19\. Soddisfazione servizi digitali|(?:23|24)\. Servizi digitali|Servizi digitali) - (?:Portale Espositori|Portale espositori|Exhibitor Portal)$',
        r'^25\. Servizi 3 - (?:Portal E-service \/ E-commerce Exhibitors|Portale E-service \/ E-commerce Unico Espositori|copy - copy - E-service\/E-commerce Portal Individual Exhibitors)$'
    ],
    'servizi_digitali_sistema_inviti_clientela': [
        r'^(?:19\. Soddisfazione servizi digitali|(?:23|24)\. Servizi digitali) - (?:Sistema inviti clientela|Sistema Inviti Clientela \(SIC\)|Customer invitation system)$'
    ],
    'servizi_digitali_app_manifestazione_lead_scanner': [
        r'^(?:24\. Servizi digitali|Servizi digitali) - App di manifestazione \(scansione rilevazione dati visitatori\)$'
    ],
    'soddisfazione_digital_platform_facilita_uso': [r"^soddisfazione digital platform - Facilità d[’']uso della piattaforma$"],
    'soddisfazione_digital_platform_pianificazione_pre_fiera': [r'^soddisfazione digital platform - Pianificazione pre-fiera$'],
    'soddisfazione_digital_platform_acquisizione_contatti_lead_scanner': [r'^soddisfazione digital platform - Facilità di acquisizione contatti \(lead scanner\)$'],
    'soddisfazione_digital_platform_profilo_buyer_incontrati': [r'^soddisfazione digital platform - Profilo e tipologia di buyer incontrati$'],
    'soddisfazione_digital_platform_stand_virtuale': [r'^soddisfazione digital platform - Creazione del proprio stand virtuale$'],
    'soddisfazione_digital_platform_appuntamenti_buyer': [r'^soddisfazione digital platform - Appuntamenti con Buyer$'],
    'soddisfazione_digital_platform_paesi_buyer_incontrati': [r'^soddisfazione digital platform - Paesi di provenienza dei buyer incontrati$'],
    'soddisfazione_digital_platform_qualita_buyer_incontrati': [r'^soddisfazione digital platform - Qualità dei buyer incontrati$'],
    # ========================================================
# ASSISTENZA COMMERCIALE E AMMINISTRATIVA
# ========================================================

'aspetti_assistenza_commerciale_e_amministrativa': [
r'^Assistenza$',
r'^Assistenza Commerciale e Amministrativa$',
r'^Assistance$',
r'^Assistance from the sales team$',
r'^Assistance from the organisational secretariat$',
r'^Assistance from the organizational secretariat$',
r'^Assistance from the organisational secretariat\s*/\s*sales team$',
r'^Assistance from the organizational secretariat\s*/\s*sales team$',
r'^Administrative services support$',
r'^Administrative services assistance.*$',
r'^Technical services support\s*\(customer care\)$',
r'^Assistenza da parte del team commerciale$',
r'^Assistenza da parte della segreteria organizzativa$',
r'^Assistenza da parte della segreteria organizzativa\s*/\s*team commerciale$',
r'^Assistenza servizi amministrativi$',
r'^Assistenza servizi tecnici\s*\(customer care\)$'
],

# ========================================================
# RISTORAZIONE / BAR
# ========================================================

'aspetti_ristorazione_bar': [
r'^Catering$',
r'^Catering\s*/\s*Bar$',
r'^Restaurants?\s*/\s*bars?$',
r'^Food and Beverage$',
r'^Ristorazione$',
r'^Ristorazione\s*/\s*Bar$'
],

# ========================================================
# LOGISTICA / SEGNALETICA / INDICAZIONI
# ========================================================

'aspetti_logistica_di_quartiere_segnaletica_indicazioni_per_orientarsi': [
r'^Venue logistics\s*/\s*Wayfinding$',
r'^Venue logistics\s*/\s*signage\s*/\s*directions.*$',
r'^Neighbourhood logistics\s*/\s*signage\s*/\s*directions.*$',
r'^Neighborhood logistics\s*/\s*signage\s*/\s*directions.*$',
r'^Logistica di quartiere\s*/\s*segnaletica\s*/\s*indicazioni.*$'
],

# ========================================================
# PULIZIA
# ========================================================

'aspetti_pulizia': [
r'^Cleaning$',
r'^Cleaning services$',
r'^Pulizia$',
r'^Servizi di pulizia$'
],

# ========================================================
# PARCHEGGI
# ========================================================

'aspetti_parcheggi': [
r'^Parking lots$',
r'^Parking spaces$',
r'^Parkings?$',
r'^Parcheggi$'
],

# ========================================================
# MISURE DI SICUREZZA
# ========================================================

'aspetti_misure_di_sicurezza': [
r'^Security measures$',
r'^Safety measures$',
r'^Misure di sicurezza$'
],

# ========================================================
# SERVIZIO DI ALLESTIMENTO STAND
# ========================================================

'aspetti_servizio_di_allestimento_stand': [
r'^Servizio di allestimento stand$',
r'^Booth setup services$',
r'^Booth set-up services$',
r'^Assistance with technical set-up services$',
r'^Assistance with technical set-up\s*/\s*customer services$',
r'^Technical and set-up services assistance$',
r'^Technical services assistance$',
r'^Pre-equipped booth assistance.*$',
r'^Pre-assembled stand assistance.*$',
r'^All-inclusive stand assistance.*$',
r'^Assistenza servizi tecnici allestitivi.*$',
r'^Assistenza stand preallestiti.*$',
r'^Assistenza stand pre-allestiti.*$',
r'^Setting up$',
r'^Allestimento$'
]

}


# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

PROTECTED_COLUMNS = {
    'aspetti_assistenza_commerciale_e_amministrativa',
    'aspetti_ristorazione_bar',
    'aspetti_logistica_di_quartiere_segnaletica_indicazioni_per_orientarsi',
    'aspetti_pulizia',
    'aspetti_parcheggi',
    'aspetti_misure_di_sicurezza',
    'aspetti_servizio_di_allestimento_stand',
    'servizi_digitali_catalogo_digital_platform',
    'servizi_digitali_fiera_id',
    'servizi_digitali_portale_espositori',
    'servizi_digitali_sistema_inviti_clientela',
    'servizi_digitali_app_manifestazione_lead_scanner',
    'soddisfazione_digital_platform_facilita_uso',
    'soddisfazione_digital_platform_pianificazione_pre_fiera',
    'soddisfazione_digital_platform_acquisizione_contatti_lead_scanner',
    'soddisfazione_digital_platform_profilo_buyer_incontrati',
    'soddisfazione_digital_platform_stand_virtuale',
    'soddisfazione_digital_platform_appuntamenti_buyer',
    'soddisfazione_digital_platform_paesi_buyer_incontrati',
    'soddisfazione_digital_platform_qualita_buyer_incontrati',
}

def should_delete(col_name):
    if col_name in PROTECTED_COLUMNS:
        return False
    return any(re.search(pattern, str(col_name), re.IGNORECASE) for pattern in to_delete_patterns)

def col_data_clean(df):
    importance_map = {
        '5': 5.0, '4': 4.0, '3': 3.0, '2': 2.0, '1': 1.0,
        'Molto importante': 5.0, 'Mediamente importante': 3.0, 'Abbastanza importante': 4.0,
        'Non molto importante': 2.0, 'Per nulla importante': 1.0,
        '5 = Molto importante': 5.0, '1 = Per nulla importante': 1.0,
        'Non un nostro obiettivo': None
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
        'Già prenotato': 5.0, 'Sicuramente sì': 5.0, 'Probabilmente sì': 4.0,
        'Forse/incerto': 3.0, 'Probabilmente no': 2.0, 'Sicuramente no': 1.0, 
        'Decisamente no': 1.0, 'Decisamente sì': 5.0, 
        5: 5.0, 4: 4.0, 3: 3.0, 2: 2.0, 1: 1.0
    }

    nps_map = {
        '10 = Sicuramente Sì': 10.0,
        '0 = Sicuramente No': 0.0
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
        
        # Importance Aspects
        'importanza_aspetti_quantita_di_visitatori': importance_map,
        'importanza_aspetti_qualita_dei_visitatori': importance_map,
        'importanza_aspetti_internazionalita_dei_visitatori': importance_map,
        'importanza_aspetti_rappresentativita_del_settore': importance_map,
        'importanza_aspetti_immagine_complessiva_della_fiera': importance_map,
        'importanza_aspetti_appearance_of_the_fair': importance_map,
        'importanza_aspetti_innovazione_di_prodotto': importance_map,
        'importanza_aspetti_programma_convegnistico': importance_map,
        
        # Satisfaction Aspects
        'soddisfazione_aspetti_quantita_di_visitatori': soddisfazione_map,
        'soddisfazione_aspetti_qualita_dei_visitatori': soddisfazione_map,
        'soddisfazione_aspetti_internazionalita_dei_visitatori': soddisfazione_map,
        'soddisfazione_aspetti_rappresentativita_del_settore': soddisfazione_map,
        'soddisfazione_aspetti_immagine_complessiva_della_fiera': soddisfazione_map,
        'soddisfazione_aspetti_appearance_of_the_fair': soddisfazione_map,
        'soddisfazione_aspetti_innovazione_di_prodotto': soddisfazione_map,
        'soddisfazione_aspetti_programma_convegnistico': soddisfazione_map,

        # Sustainability Aspects
        'sostenibilità_allestimenti_in_materiali_riutilizzabili': soddisfazione_map,
        'sostenibilità_illuminazione_a_led': soddisfazione_map,
        'sostenibilità_ristorazione_plastic_free': soddisfazione_map,
        'sostenibilità_presenza_di_espositori_che_propongono_prodotti_e_soluzioni_sostenibili': soddisfazione_map,
        'sostenibilità_organizzazione_di_conferenze_su_tematiche_relative_alla_sostenibilità': soddisfazione_map,
        'aspetti_assistenza_commerciale_e_amministrativa': aspetti_map,
        'aspetti_ristorazione_bar': aspetti_map,
        'aspetti_logistica_di_quartiere_segnaletica_indicazioni_per_orientarsi': aspetti_map,
        'aspetti_pulizia': aspetti_map,
        'aspetti_parcheggi': aspetti_map,
        'aspetti_misure_di_sicurezza': aspetti_map,
        'aspetti_servizio_di_allestimento_stand': aspetti_map,
        'servizi_digitali_catalogo_digital_platform': soddisfazione_map,
        'servizi_digitali_fiera_id': soddisfazione_map,
        'servizi_digitali_portale_espositori': soddisfazione_map,
        'servizi_digitali_sistema_inviti_clientela': soddisfazione_map,
        'servizi_digitali_app_manifestazione_lead_scanner': soddisfazione_map,
        'soddisfazione_digital_platform_facilita_uso': soddisfazione_map,
        'soddisfazione_digital_platform_pianificazione_pre_fiera': soddisfazione_map,
        'soddisfazione_digital_platform_acquisizione_contatti_lead_scanner': soddisfazione_map,
        'soddisfazione_digital_platform_profilo_buyer_incontrati': soddisfazione_map,
        'soddisfazione_digital_platform_stand_virtuale': soddisfazione_map,
        'soddisfazione_digital_platform_appuntamenti_buyer': soddisfazione_map,
        'soddisfazione_digital_platform_paesi_buyer_incontrati': soddisfazione_map,
        'soddisfazione_digital_platform_qualita_buyer_incontrati': soddisfazione_map
        
    }

    for col, current_map in mappings_config.items():
        if col in df.columns:
            # Map values converted to string layout first, fallback safely to standard float numeric
            df[col] = df[col].astype(str).str.strip().map(current_map).fillna(pd.to_numeric(df[col], errors='coerce'))
            
    return df

files = [f for f in os.listdir(input_dir) if f.endswith(('.csv', '.xlsx'))]
files.sort()

results = {}
master_dfs = []

for f in files:
    try:
        file_path = os.path.join(input_dir, f)
        if f.endswith('.csv'):
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
        else:
            df = pd.read_excel(file_path)
        
        # STEP 1: Remove the ugly backend hash IDs (e.g., [RD_aec41925...])
        tech_id_pattern = r'\s*\[[A-Z]{2}_[^\]]+\]'
        df.columns = df.columns.str.replace(tech_id_pattern, '', regex=True)
        
        # STEP 2: Convert remaining descriptive brackets to a clean hyphen format 
        # (e.g., "Obiettivi [To present]" -> "Obiettivi - To present")
        df.columns = df.columns.str.replace(r'\s*\[([^\]]+)\]', r' - \1', regex=True)

        # --- NEW STEP: Map remaining variations to unified canonical names ---
        mapped_columns = []
        for col in df.columns:
            mapped_col = col
            for canonical_name, patterns in column_mappings.items():
                for pattern in patterns:
                    descriptive_label = str(col).rsplit(' - ', 1)[-1].strip()
                    if (re.search(pattern, str(col), re.IGNORECASE)
                            or re.fullmatch(pattern, descriptive_label, re.IGNORECASE)):
                        mapped_col = canonical_name
                        break
                if mapped_col != col:
                    break
            mapped_columns.append(mapped_col)
        df.columns = mapped_columns

        
        # STEP 3: Drop unwanted columns using the updated clean names
        cols_to_drop = [c for c in df.columns if should_delete(c)]
        df_cleaned = df.drop(columns=cols_to_drop, errors='ignore')
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
                        merged = merged.combine_first(candidate)
                    combined_columns[column_name] = merged
            df_cleaned = pd.DataFrame(combined_columns, index=df_cleaned.index)
        df_cleaned = col_data_clean(df_cleaned)
        
# --- EXTRACT MANIFESTAZIONE & ANNO ---
        # Match example pattern: "2023BIT - esp_cleaned.csv" or "2026QM - Esp_cleaned.xlsx"
        match = re.match(r'(\d{4})([^- ]+)', f)
        if match:
            year_val = match.group(1)
            exhibition_val = match.group(2)
        else:
            year_val = "Unknown"
            exhibition_val = "Unknown"
            
        # Add tracking metadata columns
        df_cleaned['Manifestazione'] = exhibition_val
        df_cleaned['Anno'] = year_val
        
        # --- TARGET SCHEMA ENFORCEMENT (INDIVIDUAL FILE LEVEL) ---
        # Instantly remove columns not matching our allowed BigQuery destination template
        extra_cols = [c for c in df_cleaned.columns if c not in TARGET_SCHEMA]
        if extra_cols:
            df_cleaned = df_cleaned.drop(columns=extra_cols)

        for target_column in TARGET_SCHEMA:
            if target_column not in df_cleaned.columns:
                df_cleaned[target_column] = pd.NA
        df_cleaned = df_cleaned[TARGET_SCHEMA]

        # Save structural changes locally
        name_part, ext_part = os.path.splitext(f)
        cleaned_filename = f"{name_part}_cleaned{ext_part}"
        output_path = os.path.join(output_dir, cleaned_filename)
        
        if f.endswith('.csv'):
            df_cleaned.to_csv(output_path, index=False)
        else:
            df_cleaned.to_excel(output_path, index=False)
            
        # Append to master collection list
        master_dfs.append(df_cleaned)
        
        # Structuring summary details
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

# Save structural overview report safely
with open(os.path.join(output_dir, 'summary.txt'), 'w', encoding='utf-8') as f_out:
    for year in sorted(results.keys()):
        f_out.write(f"Year: {year}\n")
        for exhibition in sorted(results[year].keys()):
            f_out.write(f"  Exhibition: {exhibition}\n")
            for entry in results[year][exhibition]:
                f_out.write(f"    File: {entry['filename']}\n")
                f_out.write(f"    Columns: {', '.join(entry['columns'])}\n")
        f_out.write("-" * 40 + "\n")

print("Processing complete. Cleaned files saved locally.")

# --- BIGQUERY INGESTION STAGE ---
if master_dfs:
    print("\nConsolidating structural matrices for BigQuery migration...")
    
    # concat automatically builds a global unique list of columns, inserting nulls/NaNs where datasets differ
    master_df = pd.concat(master_dfs, ignore_index=True, sort=False)
    
    # Define columns that must be treated as strict strings
    string_columns = ['Manifestazione', 'Anno', 'company_name', 'elemento_top', 'elemento_flop']
    
    # Explicitly enforce types column by column before sending to BigQuery
    for col in master_df.columns:
        if col in string_columns:
            # Cast as strict string and handle null strings so they map to NULL in BigQuery
            master_df[col] = master_df[col].astype(str).replace(['nan', 'None', '<NA>'], None)
        else:
            # Convert to float, keeping values as they are, coercing any unmapped text to NaN (NULL)
            master_df[col] = pd.to_numeric(master_df[col], errors='coerce').astype(float)
            
    try:
        print(f"Initiating Google Cloud BigQuery client connection...")
        client = bigquery.Client(project=PROJECT_ID)
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        # Ingestion setup options configuration
        job_config = bigquery.LoadJobConfig(
            # Auto-detect constructs safe schemas natively based on dataframe column types
            autodetect=True,
            # WRITE_TRUNCATE overwrites previous attempts; change to WRITE_APPEND if preferred
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        )
        
        print(f"Uploading massive matrix ({master_df.shape[0]} rows x {master_df.shape[1]} columns) to {table_ref}...")
        job = client.load_table_from_dataframe(master_df, table_ref, job_config=job_config)
        job.result()  # Blocks executions gracefully until data pipeline clears
        
        print(f"Success! Finalized pipeline safely uploaded to BigQuery table: {TABLE_ID}")
        
    except Exception as bq_err:
        print(f"Pipeline Upload Exception to Google BigQuery: {bq_err}")
else:
    print("Execution halt: No distinct datasets compiled for database parsing matrix updates.")