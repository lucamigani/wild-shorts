# Wild Shorts

Ogni giorno crea un video verticale "What would you do?" a tema sopravvivenza, lo manda su Telegram e, se approvi, lo pubblica come Reel su Instagram.

## Come funziona
1. Parte dalle 6 mini-storie con fonte, poi passa ai quiz con clip stock e infine alle bozze Gemini.
2. Crea il video e un audio di vento originale.
3. Ti invia il video su Telegram con i pulsanti Pubblica e Scarta.
4. Ogni 15 minuti legge la tua scelta e pubblica su Instagram.
5. Ti manda il testo da usare per caricare a mano su YouTube e TikTok.

## Configurazione
1. Crea un repository GitHub **pubblico** e carica questi file. Il repository, e i video in attesa di approvazione, saranno visibili a tutti. Non scrivere mai chiavi nei file.
2. Crea una chiave gratuita Pixabay e una Gemini su Google AI Studio.
3. Su Telegram crea un bot con @BotFather, poi scrivigli un messaggio. Il tuo ID numerico è il `TELEGRAM_CHAT_ID`, che puoi leggere con @userinfobot.
4. Passa Instagram a un account professionale, crea un'app su Meta for Developers con Business Login for Instagram e il permesso `instagram_business_content_publish`, poi genera il token.
5. In GitHub, in Settings > Secrets and variables > Actions, aggiungi `PIXABAY_API_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `IG_USER_ID`, `IG_ACCESS_TOKEN`.
6. In Settings > Actions > General, imposta i permessi del workflow su "Read and write".
7. Nella scheda Actions avvia "Generate reel" con Run workflow.

## Regole da rispettare
- Prima di approvare, controlla ogni risposta su una fonte ufficiale, come parchi nazionali o guardia costiera. Nessuno scenario è stato ancora verificato su fonti.
- Non aggiungere video di altri creator.
- Se scegli musica di tendenza, aggiungila a mano dall'app della piattaforma.

## Prova locale
```
pip install -r requirements.txt
python -m unittest discover -s tests -t .
python -m bot.main preview 3
```
