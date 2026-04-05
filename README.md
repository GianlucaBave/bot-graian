# Graian Capital — Portfolio Analytics Agent

Un agente conversazionale costruito con **Claude + Streamlit** per analizzare dati di portafoglio di prestiti (loan portfolios) di Graian Capital Management, Lugano.

---

## Struttura del repo

```
bot-graian/
├── app.py                  # App principale: UI Streamlit + agente Claude
├── clean_data.py           # Script di pulizia dati (eseguire una volta)
├── .env                    # API key Anthropic (non committare)
│
├── business case copia.xlsx   # Sorgente dati principale (transazioni, prodotti, portafogli)
├── fx copia.csv               # Tassi di cambio EURUSD storici
├── prices.csv                 # NAV mensili dei portafogli
│
├── clean_transactions.csv  # Output pulizia: transazioni
├── clean_products.csv      # Output pulizia: prodotti
├── clean_portfolios.csv    # Output pulizia: portafogli
├── clean_fx.csv            # Output pulizia: FX
└── clean_prices.csv        # Output pulizia: prezzi/NAV
```

---

## Pipeline dati (`clean_data.py`)

Prima di avviare l'app, i dati grezzi vengono puliti con `python3 clean_data.py`. Lo script:

| Dataset | Fonte | Operazioni principali |
|---|---|---|
| **transactions** | Excel (sheet `transactions`) | Normalizzazione stringhe, conversione tipi, fix prezzo = 0 → 1, tagging LEGACY/CURRENT, drop null |
| **products** | Excel (sheet `products`) | Normalizzazione, deduplicazione su `product-code` |
| **portfolios** | Excel (sheet `portfolios`) | Normalizzazione, deduplicazione |
| **fx** | `fx copia.csv` | Parsing date (formato `dd.mm.yyyy`), forward-fill dei valori EURUSD nulli |
| **prices** | `prices.csv` | Parsing date, sostituzione zero con null per P2-USD (era in pre-funding) |

### Problemi di qualità dati noti

1. 1 transazione con `transaction-price = 0` → corretto a 1
2. 5 valori FX null → riempiti con il valore precedente (forward-fill)
3. 18 codici transazione legacy (non iniziano con `TR-`) → taggati come `LEGACY`
4. Prodotto `PR-P4N4N` ha `loan-property-value-ratio = 33.33` (outlier) → escluso dai calcoli LTV
5. `P2-USD` mostra valori zero maggio–agosto 2021 → sostituiti con null (portafoglio in pre-funding)
6. `P1-EUR` luglio 2021 ha un calo NAV del -49.5% → mantenuto nel dato, segnalato come anomalia

---

## Come funziona l'agente (`app.py`)

### Architettura

```
Utente (chat) → Streamlit UI
                    ↓
             Claude (Haiku 4.5)
                    ↓
          Tool-use loop (agentic)
                    ↓
         Tool Python → dati CSV
                    ↓
          Risposta testuale + grafici
```

### Flusso di esecuzione

1. L'utente scrive una domanda nella chat
2. Il messaggio viene inviato a Claude con il **system prompt** e la lista degli **strumenti disponibili**
3. Claude decide se rispondere direttamente o chiamare uno o più strumenti
4. Se `stop_reason == "tool_use"`, l'app:
   - esegue la funzione Python corrispondente
   - restituisce il risultato a Claude come `tool_result`
   - ripete il ciclo finché Claude non risponde in modo finale
5. La risposta testuale viene mostrata in chat; i grafici Plotly vengono renderizzati sotto

### Strumenti disponibili

| Tool | Descrizione |
|---|---|
| `get_loan_exposure` | Esposizione totale sui prestiti (qty × price) per portafoglio |
| `get_loan_exposure_by_issuer` | Esposizione raggruppata per emittente, ordinata decrescente |
| `get_ltv` | LTV medio per portafoglio (= 1 / loan-property-value-ratio), outlier esclusi |
| `get_portfolio_value` | NAV più recente del portafoglio a una data |
| `get_loan_exposure_pct` | Esposizione prestiti come % del NAV |
| `get_fx_rate` | Tasso EURUSD alla data richiesta |
| `plot_exposure_trend` | Grafico lineare: esposizione cumulativa nel tempo |
| `plot_issuer_breakdown` | Grafico a barre orizzontali: esposizione per emittente |
| `plot_ltv_by_issuer` | Grafico a barre: LTV medio per emittente con soglia 80% |
| `get_data_quality_summary` | Riepilogo dei problemi di qualità dati e correzioni applicate |

### Dati coperti

- **Portafogli**: `P1-EUR`, `P2-USD`
- **Periodo**: maggio 2021 – giugno 2022
- **Tipo prodotti analizzati**: solo `LN` (loan products)

---

## Installazione e avvio

```bash
# 1. Installa dipendenze
pip3 install anthropic streamlit pandas numpy plotly python-dotenv

# 2. Crea il file .env con la tua API key Anthropic
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env

# 3. Pulisci i dati grezzi (solo la prima volta)
python3 clean_data.py

# 4. Avvia l'app
python3 -m streamlit run app.py
```

L'app sarà disponibile su `http://localhost:8501`.

---

## Esempi di domande

- *"Qual è l'esposizione totale sui prestiti al 31 dicembre 2021?"*
- *"Mostrami il breakdown per emittente del portafoglio P1-EUR"*
- *"Qual è il LTV medio di P2-USD?"*
- *"Genera un grafico dell'andamento dell'esposizione nel tempo"*
- *"Ci sono problemi di qualità nei dati?"*
