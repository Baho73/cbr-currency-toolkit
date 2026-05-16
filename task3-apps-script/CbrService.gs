// FILE: task3-apps-script/CbrService.gs
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Получение и разбор курсов валют ЦБ РФ через UrlFetchApp с обработкой ошибок.
//   SCOPE: Класс CbrService: HTTP-запрос, проверка кода ответа, парсинг и валидация JSON.
//   DEPENDS: M-T3-CONFIG
//   LINKS: M-T3-CBR-SERVICE
//   ROLE: RUNTIME
//   MAP_MODE: NONE
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   CbrService - класс получения курсов; метод fetchRates() -> { date, rows }
// END_MODULE_MAP
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.0.0 - Первичная реализация сервиса получения курсов.
// END_CHANGE_SUMMARY

/**
 * Сервис получения курсов валют ЦБ РФ.
 * Инкапсулирует работу с UrlFetchApp и разбор ответа в строки таблицы.
 */
class CbrService {
  /**
   * @param {!Object} config — объект CONFIG.
   */
  constructor(config) {
    this.config = config;
  }

  /**
   * Загрузить и разобрать актуальные курсы валют.
   * @return {{date: string, rows: !Array<!Array>}} дата снимка и строки курсов.
   * @throws {Error} при недоступности API, неуспешном коде или некорректном формате.
   */
  fetchRates() {
    // START_BLOCK_FETCH_RATES
    let response;
    try {
      // muteHttpExceptions: true — не бросать на 4xx/5xx, проверим код вручную.
      response = UrlFetchApp.fetch(this.config.API_URL, {
        muteHttpExceptions: true,
        followRedirects: true,
      });
    } catch (err) {
      throw new Error('Не удалось обратиться к API ЦБ РФ: ' + err.message);
    }

    const statusCode = response.getResponseCode();
    if (statusCode !== 200) {
      throw new Error('API ЦБ РФ вернул код ответа ' + statusCode);
    }

    let payload;
    try {
      payload = JSON.parse(response.getContentText());
    } catch (err) {
      throw new Error('Ответ API не является корректным JSON');
    }

    if (!payload || typeof payload.Valute !== 'object' || payload.Valute === null) {
      throw new Error('В ответе API отсутствует объект "Valute"');
    }
    // END_BLOCK_FETCH_RATES

    return this.parseRates_(payload);
  }

  /**
   * Преобразовать тело ответа API в строки таблицы.
   * @param {!Object} payload — разобранный JSON-ответ.
   * @return {{date: string, rows: !Array<!Array>}}
   * @private
   */
  parseRates_(payload) {
    const rows = Object.keys(payload.Valute).map((key) => {
      const item = payload.Valute[key];
      const deltaAbs = item.Value - item.Previous;
      // Защита от деления на ноль при отсутствующем/нулевом предыдущем курсе.
      const deltaPct = item.Previous ? (deltaAbs / item.Previous) * 100 : 0;
      return [
        item.CharCode,
        item.Name,
        item.Nominal,
        item.Value,
        Number(deltaAbs.toFixed(4)),
        Number(deltaPct.toFixed(2)),
      ];
    });

    // Сортировка по коду валюты — стабильный порядок строк в таблице.
    rows.sort((a, b) => String(a[0]).localeCompare(String(b[0])));
    return { date: payload.Date || '', rows: rows };
  }
}
