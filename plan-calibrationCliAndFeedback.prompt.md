## Plan: Calibrazione CLI e feedback migliorato

TL;DR: Rendere la calibrazione una feature di primo livello nella CLI riusando `calibration.calibrate()` e `calibration.write_corrected_cube()`, e migliorare `inspect` e `batch` con output piu strutturato, classificazione degli errori e warning sui dati XMP non supportati.

**Steps**
1. Definire il comando CLI di calibrazione in [python/xmp_to_lut/cli.py] seguendo il pattern di `convert`, `inspect` e `batch`.
   - Aggiungere un subcommand `calibrate` con input `simulated_cube` e `processed_hald`, opzioni `--level`, `--output` e `--title`.
   - Comportamento consigliato: senza `--output` mostra solo il report; con `--output` scrive una `.cube` corretta.
   - Riusare `CalibrationReport.summary()` e mantenere `ClickException` per input non validi.
2. Collegare il comando alla pipeline esistente in [python/xmp_to_lut/calibration.py].
   - Validare il match tra size della cube e `level ** 2` prima di scrivere.
   - Distinguere chiaramente errori di parsing cube, lettura HALD e I/O in modo che la CLI restituisca messaggi d'errore stabili.
3. Migliorare `inspect` in [python/xmp_to_lut/cli.py] con un riepilogo piu leggibile.
   - Raggruppare i campi per area funzionale: white balance, basic, color, tone curves, HSL, split toning.
   - Mostrare numero di campi modificati vs invariati e mettere in evidenza curve non lineari.
   - Aggiungere warning opzionali quando il file contiene valori sospetti o proprieta non tradotte, se si introduce il supporto diagnostico nel parser.
4. Migliorare `batch` in [python/xmp_to_lut/cli.py] per rendere il risultato piu utile su directory grandi.
   - Classificare i fallimenti in parsing, conversione engine e I/O.
   - Aggiungere un riepilogo finale con conteggi per categoria, non solo converted/failed.
   - Valutare una modalita `--verbose` per mostrare il dettaglio del primo errore per file senza inondare l'output.
5. Estendere il parser se serve per supportare warning sui campi XMP ignorati.
   - Aggiungere diagnostica in [python/xmp_to_lut/parser.py] e [python/xmp_to_lut/mappings.py] senza rompere `parse_xmp()` come API principale.
   - Esportare eventuali warning come helper separato cosi `inspect` e `batch` possono usarli senza cambiare il flusso attuale.
6. Aggiornare test e documentazione in parallelo con le modifiche.
   - Coprire il nuovo comando calibration e i nuovi casi di output di `inspect`/`batch` in [tests/test_cli.py].
   - Aggiungere test mirati in [tests/test_calibration.py] se cambiano i messaggi o i rami di validazione.
   - Aggiornare gli esempi d'uso in [README.md].

**Relevant files**
- [python/xmp_to_lut/cli.py] — nuovi subcommand, formatting output, error handling.
- [python/xmp_to_lut/calibration.py] — pipeline di confronto, report, scrittura cube corretta.
- [python/xmp_to_lut/parser.py] — eventuale diagnostica su proprieta non supportate.
- [python/xmp_to_lut/mappings.py] — sorgente delle proprieta riconosciute.
- [tests/test_cli.py] — copertura dei nuovi flussi CLI.
- [tests/test_calibration.py] — validazione report e file output.
- [README.md] — uso dei nuovi comandi e opzioni.

**Verification**
1. Aggiungere test CLI per `calibrate` in modalita compare-only e write-to-file.
2. Aggiungere test per `inspect` che verifichino i nuovi riepiloghi e warning.
3. Aggiungere test per `batch` con mix di successi/fallimenti e conteggi per categoria.
4. Eseguire il subset piu קטן possibile di `pytest` sui file toccati.
5. Se il parser viene esteso, aggiungere un test che confermi che i warning non rompono il comportamento attuale di `parse_xmp()`.

**Decisions**
- Il comando di calibrazione sara esposto come un solo comando `calibrate` con output opzionale, invece di due comandi separati, per restare coerente con l'attuale CLI.
- Il cambiamento di punto 2 rimarra focalizzato su output e diagnostica; non introduce nuove funzionalita di filesystem come batch ricorsivo o overwrite in questa fase.
- Le warning sui campi non supportati richiedono un piccolo strato diagnostico nel parser; se non serve nel primo taglio, si puo rimandare senza bloccare `inspect` e `batch`.
