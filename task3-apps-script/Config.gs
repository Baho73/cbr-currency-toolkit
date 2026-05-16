// FILE: task3-apps-script/Config.gs
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Константы конфигурации Apps Script: URL API, имя листа, заголовки столбцов, разметка ячеек.
//   SCOPE: Единственный замороженный объект CONFIG, доступный всем .gs-файлам проекта.
//   DEPENDS: none
//   LINKS: M-T3-CONFIG
//   ROLE: CONFIG
//   MAP_MODE: NONE
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   CONFIG - замороженный объект констант конфигурации
// END_MODULE_MAP
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.0.0 - Первичная реализация конфигурации.
// END_CHANGE_SUMMARY

/**
 * Конфигурация скрипта выгрузки курсов валют ЦБ РФ.
 * Object.freeze защищает константы от случайной мутации в рантайме.
 *
 * Разметка листа:
 *   A1            — ячейка статуса последнего обновления;
 *   A2            — дата снимка курсов ЦБ РФ;
 *   строка 3      — заголовки столбцов;
 *   строки 4+     — данные курсов.
 */
const CONFIG = Object.freeze({
  API_URL: 'https://www.cbr-xml-daily.ru/daily_json.js',
  SHEET_NAME: 'Курсы ЦБ РФ',
  STATUS_CELL: 'A1',
  DATE_CELL: 'A2',
  HEADER_ROW: 3,
  DATA_START_ROW: 4,
  HEADERS: Object.freeze([
    'Код',
    'Валюта',
    'Номинал',
    'Курс ЦБ, ₽',
    'Изменение за сутки, ₽',
    'Изменение, %',
  ]),
  COLOR_OK: '#1f9d57',
  COLOR_ERROR: '#d8453b',
});
