// FILE: task3-apps-script/SheetWriter.gs
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Запись курсов валют в столбцы Google Таблицы и обновление ячейки статуса.
//   SCOPE: Класс SheetWriter: writeRates (данные + заголовки) и writeStatus (статус/ошибка).
//   DEPENDS: M-T3-CONFIG
//   LINKS: M-T3-SHEET-WRITER
//   ROLE: RUNTIME
//   MAP_MODE: NONE
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   SheetWriter - класс записи в таблицу; методы writeRates(result), writeStatus(message, isError)
// END_MODULE_MAP
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.0.0 - Первичная реализация записи в таблицу.
// END_CHANGE_SUMMARY

/**
 * Записывает курсы валют и статус выполнения в лист Google Таблицы.
 */
class SheetWriter {
  /**
   * @param {!Sheet} sheet — целевой лист таблицы.
   * @param {!Object} config — объект CONFIG.
   */
  constructor(sheet, config) {
    this.sheet = sheet;
    this.config = config;
  }

  /**
   * Записать курсы валют в столбцы: дату, заголовки и строки данных.
   * Старые данные предварительно очищаются, чтобы не оставлять «хвостов».
   * @param {{date: string, rows: !Array<!Array>}} result — результат CbrService.fetchRates().
   */
  writeRates(result) {
    // START_BLOCK_WRITE_RATES
    const config = this.config;
    const columnCount = config.HEADERS.length;

    // Очистка прежнего диапазона данных (на случай уменьшения числа валют).
    const lastRow = this.sheet.getLastRow();
    if (lastRow >= config.DATA_START_ROW) {
      this.sheet
        .getRange(config.DATA_START_ROW, 1, lastRow - config.DATA_START_ROW + 1, columnCount)
        .clearContent();
    }

    // Дата снимка курсов.
    this.sheet.getRange(config.DATE_CELL).setValue('Курсы на дату: ' + result.date);

    // Заголовки столбцов.
    this.sheet
      .getRange(config.HEADER_ROW, 1, 1, columnCount)
      .setValues([config.HEADERS])
      .setFontWeight('bold');

    // Строки данных — пакетная запись одним вызовом setValues (быстро и атомарно).
    if (result.rows.length > 0) {
      this.sheet
        .getRange(config.DATA_START_ROW, 1, result.rows.length, columnCount)
        .setValues(result.rows);
    }
    this.sheet.autoResizeColumns(1, columnCount);
    // END_BLOCK_WRITE_RATES
  }

  /**
   * Записать статус последнего запуска в выделенную ячейку.
   * @param {string} message — текст статуса.
   * @param {boolean} isError — true для ошибки (красный цвет), false для успеха (зелёный).
   */
  writeStatus(message, isError) {
    const cell = this.sheet.getRange(this.config.STATUS_CELL);
    cell.setValue(message);
    cell.setFontWeight('bold');
    cell.setFontColor(isError ? this.config.COLOR_ERROR : this.config.COLOR_OK);
  }
}
