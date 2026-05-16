// FILE: task3-apps-script/Main.gs
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Точка входа Apps Script: кастомное меню и функция обновления курсов по триггеру.
//   SCOPE: onOpen (меню), updateRates (оркестрация fetch -> write -> status), helper листа.
//   DEPENDS: M-T3-CONFIG, M-T3-CBR-SERVICE, M-T3-SHEET-WRITER
//   LINKS: M-T3-MAIN
//   ROLE: SCRIPT
//   MAP_MODE: NONE
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   onOpen - добавляет кастомное меню при открытии таблицы (simple trigger)
//   updateRates - основная функция: загрузка курсов и запись в таблицу
//   getOrCreateSheet_ - helper: получить или создать целевой лист
// END_MODULE_MAP
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.0.0 - Первичная реализация точки входа.
// END_CHANGE_SUMMARY

/**
 * Simple trigger: при открытии таблицы добавляет кастомное меню.
 * Через это меню пользователь запускает обновление курсов вручную.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Курсы ЦБ РФ')
    .addItem('Обновить курсы', 'updateRates')
    .addToUi();
}

/**
 * Основная функция: загружает курсы валют ЦБ РФ и записывает их в таблицу.
 *
 * Вызывается двумя способами:
 *   1) вручную — пункт меню «Курсы ЦБ РФ → Обновить курсы»;
 *   2) автоматически — устанавливаемый time-driven триггер (см. README).
 *
 * Любая ошибка перехватывается и записывается в ячейку статуса — выполнение
 * не падает «тихо», а оставляет видимый человекочитаемый след в таблице.
 */
function updateRates() {
  const sheet = getOrCreateSheet_(CONFIG);
  const writer = new SheetWriter(sheet, CONFIG);

  try {
    // START_BLOCK_UPDATE_RATES
    const service = new CbrService(CONFIG);
    const result = service.fetchRates();
    writer.writeRates(result);
    writer.writeStatus(
      'Обновлено ' + formatNow_() + '. Валют: ' + result.rows.length,
      false
    );
    // END_BLOCK_UPDATE_RATES
  } catch (err) {
    // Ошибка видна пользователю прямо в таблице (ячейка статуса).
    writer.writeStatus('Ошибка (' + formatNow_() + '): ' + err.message, true);
  }
}

/**
 * Получить целевой лист по имени из CONFIG или создать его, если он отсутствует.
 * @param {!Object} config — объект CONFIG.
 * @return {!Sheet} лист для записи курсов.
 * @private
 */
function getOrCreateSheet_(config) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName(config.SHEET_NAME);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(config.SHEET_NAME);
  }
  return sheet;
}

/**
 * Отформатировать текущий момент времени для строки статуса.
 * @return {string} дата и время в локали ru-RU.
 * @private
 */
function formatNow_() {
  return Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    'dd.MM.yyyy HH:mm:ss'
  );
}
