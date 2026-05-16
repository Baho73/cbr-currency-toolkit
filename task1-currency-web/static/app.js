// FILE: task1-currency-web/static/app.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Клиентская логика конвертера: загрузка курсов и конвертация через REST API.
//   SCOPE: Класс ApiClient (обёртка fetch) и ConverterController (связывание DOM, рендер).
//   DEPENDS: M-T1-API
//   LINKS: M-T1-FRONTEND
//   ROLE: UI_COMPONENT
//   MAP_MODE: EXPORTS
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   ApiClient - async-обёртка над fetch к эндпоинтам /api/*
//   ConverterController - связывание DOM, валидация ввода, рендер курсов и результата
// END_MODULE_MAP
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.0.0 - Первичная реализация клиентской логики.
// END_CHANGE_SUMMARY
"use strict";

/**
 * Тонкая async-обёртка над REST API конвертера.
 * Изолирует работу с сетью от логики интерфейса.
 */
class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  /** Загрузить актуальный снимок курсов валют. */
  async getRates() {
    return this.#request("/api/rates");
  }

  /** Сконвертировать сумму между валютами. */
  async convert(amount, fromCode, toCode) {
    return this.#request("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount, from_code: fromCode, to_code: toCode }),
    });
  }

  /** Выполнить запрос и привести ошибки API к единому Error с сообщением. */
  async #request(path, options = {}) {
    let response;
    try {
      response = await fetch(this.baseUrl + path, options);
    } catch {
      throw new Error("Сервер недоступен. Проверьте подключение.");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Ошибка запроса (код ${response.status})`);
    }
    return data;
  }
}

/**
 * Контроллер интерфейса: связывает элементы DOM, валидирует ввод,
 * запрашивает данные через ApiClient и рендерит результат.
 */
class ConverterController {
  constructor(apiClient) {
    this.api = apiClient;
    this.el = {
      amount: document.getElementById("amount"),
      fromCode: document.getElementById("from-code"),
      toCode: document.getElementById("to-code"),
      swap: document.getElementById("swap"),
      convert: document.getElementById("convert"),
      result: document.getElementById("result"),
      ratesBody: document.getElementById("rates-body"),
      ratesDate: document.getElementById("rates-date"),
      errorBanner: document.getElementById("error-banner"),
    };
  }

  /** Инициализация: навесить обработчики и загрузить курсы. */
  async init() {
    this.el.convert.addEventListener("click", () => this.onConvert());
    this.el.swap.addEventListener("click", () => this.onSwap());
    await this.loadRates();
  }

  /** Загрузить курсы, заполнить выпадающие списки и таблицу. */
  async loadRates() {
    try {
      const data = await this.api.getRates();
      this.#populateSelects(data.rates);
      this.#renderRatesTable(data.rates);
      this.el.ratesDate.textContent = this.#formatDate(data.date);
      this.#hideError();
    } catch (error) {
      this.#showError(`Не удалось загрузить курсы: ${error.message}`);
      this.el.ratesBody.innerHTML =
        '<tr><td colspan="4" class="rates__loading">Курсы недоступны</td></tr>';
    }
  }

  /** Обработчик конвертации: валидация ввода и запрос к API. */
  async onConvert() {
    const amount = Number.parseFloat(this.el.amount.value);
    if (!Number.isFinite(amount) || amount <= 0) {
      this.#showError("Введите положительную сумму.");
      return;
    }
    this.el.convert.disabled = true;
    try {
      const data = await this.api.convert(
        amount, this.el.fromCode.value, this.el.toCode.value
      );
      this.#renderResult(data);
      this.#hideError();
    } catch (error) {
      this.#showError(`Ошибка конвертации: ${error.message}`);
      this.el.result.hidden = true;
    } finally {
      this.el.convert.disabled = false;
    }
  }

  /** Поменять валюты в списках местами. */
  onSwap() {
    const from = this.el.fromCode.value;
    this.el.fromCode.value = this.el.toCode.value;
    this.el.toCode.value = from;
  }

  /** Заполнить оба выпадающих списка валютами. */
  #populateSelects(rates) {
    const options = rates
      .map((r) => `<option value="${r.code}">${r.code} — ${r.name}</option>`)
      .join("");
    this.el.fromCode.innerHTML = options;
    this.el.toCode.innerHTML = options;
    this.el.fromCode.value = "USD";
    this.el.toCode.value = "RUB";
  }

  /** Отрендерить таблицу курсов с цветовой подсветкой динамики. */
  #renderRatesTable(rates) {
    this.el.ratesBody.innerHTML = rates
      .map((r) => {
        const dir = r.delta_abs > 0 ? "up" : r.delta_abs < 0 ? "down" : "flat";
        const sign = r.delta_abs > 0 ? "+" : "";
        return `<tr>
          <td><code>${r.code}</code></td>
          <td>${r.name}</td>
          <td class="num">${r.value.toFixed(4)}</td>
          <td class="num delta--${dir}">${sign}${r.delta_pct.toFixed(2)}%</td>
        </tr>`;
      })
      .join("");
  }

  /** Показать результат конвертации. */
  #renderResult(data) {
    this.el.result.innerHTML =
      `${data.amount} ${data.from_code} = <strong>${data.result.toFixed(4)} ${data.to_code}</strong>` +
      `<span class="result__rate">Курс: 1 ${data.from_code} = ${data.rate} ${data.to_code}</span>`;
    this.el.result.hidden = false;
  }

  #formatDate(isoString) {
    const date = new Date(isoString);
    return Number.isNaN(date.getTime())
      ? isoString
      : date.toLocaleDateString("ru-RU");
  }

  #showError(message) {
    this.el.errorBanner.textContent = message;
    this.el.errorBanner.hidden = false;
  }

  #hideError() {
    this.el.errorBanner.hidden = true;
  }
}

// Точка входа: запуск контроллера после готовности DOM.
document.addEventListener("DOMContentLoaded", () => {
  new ConverterController(new ApiClient()).init();
});
