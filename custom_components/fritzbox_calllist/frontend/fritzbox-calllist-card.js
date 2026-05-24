(function () {
const CARD_TYPE = "fritzbox-calllist-card";
const DEFAULT_ENTITY = "sensor.fritzbox_calllist";
const DEFAULT_MAX_ITEMS = 4;
const DEFAULT_FONT_SIZE = 14;

const TRANSLATIONS = {
  de: {
    title: "Telefon",
    empty: "Keine Anrufe vorhanden",
    before: "vor",
    seconds: "sekunden",
    minutes: "minuten",
    hours: "stunden",
    days: "tagen",
    unknown: "Unbekannt",
    ringing: "Anruf von",
    dialing: "Anruf an",
    talking: "Gespräch mit",
    outgoing: "Gespräch mit",
    incoming: "Anruf von",
    missed: "Verpasster Anruf von",
    notAnswered: "Nicht angenommen an",
    errorEntity: "Bitte eine FRITZ!Box-Calllist-Entity angeben.",
    editorEntity: "Entity",
    editorTitle: "Titel",
    editorMaxItems: "Einträge",
    editorFontSize: "Schriftgröße",
    editorLanguage: "Sprache",
    langAuto: "Automatisch",
    langGerman: "Deutsch",
    langEnglish: "Englisch",
    cardDescription: "Zeigt Live-Anrufe und den Telefonverlauf aus der FRITZ!Box-Calllist-Integration.",
  },
  en: {
    title: "Phone",
    empty: "No calls available",
    before: "ago",
    seconds: "seconds",
    minutes: "minutes",
    hours: "hours",
    days: "days",
    unknown: "Unknown",
    ringing: "Call from",
    dialing: "Call to",
    talking: "Call with",
    outgoing: "Call with",
    incoming: "Call from",
    missed: "Missed call from",
    notAnswered: "Not answered to",
    errorEntity: "Please provide a FRITZ!Box Calllist entity.",
    editorEntity: "Entity",
    editorTitle: "Title",
    editorMaxItems: "Entries",
    editorFontSize: "Font size",
    editorLanguage: "Language",
    langAuto: "Automatic",
    langGerman: "German",
    langEnglish: "English",
    cardDescription: "Shows live calls and call history from the FRITZ!Box Calllist integration.",
  },
};

function normalizeLanguage(value) {
  return String(value || "en").toLowerCase().startsWith("de") ? "de" : "en";
}

class FritzboxCalllistCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("fritzbox-calllist-card-editor");
  }

  static getStubConfig() {
    return {
      entity: DEFAULT_ENTITY,
      max_items: DEFAULT_MAX_ITEMS,
      font_size: DEFAULT_FONT_SIZE,
      language: "auto",
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error(this.localize().errorEntity);
    }

    this.config = {
      max_items: DEFAULT_MAX_ITEMS,
      font_size: DEFAULT_FONT_SIZE,
      language: "auto",
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  connectedCallback() {
    this._timer = window.setInterval(() => this.render(), 1000);
  }

  disconnectedCallback() {
    if (this._timer) {
      window.clearInterval(this._timer);
      this._timer = undefined;
    }
  }

  getCardSize() {
    return 3;
  }

  render() {
    if (!this.config || !this._hass) {
      return;
    }

    const entity = this._hass.states[this.config.entity];
    const attrs = entity?.attributes || {};
    const history = Array.isArray(attrs.history) ? attrs.history : [];
    const live = attrs.live || null;
    const isActive = Boolean(attrs.is_active && live);
    const limit = Math.max(1, Number(this.config.max_items || 4)) - (isActive ? 1 : 0);
    const texts = this.localize();
    const title = this.config.title || texts.title;
    const fontSize = Math.max(10, Math.min(24, Number(this.config.font_size || DEFAULT_FONT_SIZE)));

    const liveHtml = isActive ? this.renderLive(live) : "";
    const historyHtml = history.slice(0, limit).map((call) => this.renderHistory(call)).join("");
    const emptyHtml = !isActive && !history.length ? `<div class="empty">${texts.empty}</div>` : "";

    this.innerHTML = `
      <ha-card>
        <div class="card">
          <div class="header">${this.escape(title)}</div>
          ${liveHtml}
          ${isActive && history.length ? `<div class="divider"></div>` : ""}
          <div class="history">${historyHtml}${emptyHtml}</div>
        </div>
      </ha-card>
      <style>
        :host {
          display: block;
        }

        .card {
          --fritzbox-calllist-font-size: ${fontSize}px;
          padding: 16px;
        }

        .header {
          color: var(--primary-text-color);
          font-size: 18px;
          font-weight: 500;
          line-height: 24px;
          margin-bottom: 12px;
        }

        .live-call {
          align-items: center;
          color: var(--primary-text-color);
          font-size: var(--fritzbox-calllist-font-size);
          display: grid;
          gap: 10px;
          grid-template-columns: 28px 1fr;
          min-height: 32px;
          font-weight: 500;
        }

        .history-row {
          align-items: center;
          color: var(--primary-text-color);
          font-size: var(--fritzbox-calllist-font-size);
          display: grid;
          gap: 10px;
          grid-template-columns: 28px 1fr;
          min-height: 32px;
        }

        ha-icon {
          display: inline-flex;
          height: 24px;
          width: 24px;
        }

        .label {
          font-size: var(--fritzbox-calllist-font-size);
          min-width: 0;
          overflow-wrap: anywhere;
        }

        .live-content,
        .history-content {
          min-width: 0;
        }

        .meta,
        .duration {
          color: #7e7e7e;
          font-size: max(11px, calc(var(--fritzbox-calllist-font-size) - 2px));
          white-space: nowrap;
        }

        .duration {
          font-variant-numeric: tabular-nums;
        }

        .history {
          display: grid;
          gap: 8px;
        }

        .empty {
          color: #7e7e7e;
          font-size: 14px;
        }

        .ringing {
          color: #b22222;
          animation: blink 1s infinite steps(1, start);
        }

        .dialing {
          color: #32a054;
          animation: spin 2.5s infinite linear;
        }

        .talking {
          color: #337ab7;
        }

        .outgoing {
          color: #32a054;
        }

        .incoming {
          color: #337ab7;
        }

        .missed {
          color: #b22222;
        }

        .not_answered {
          color: #ffa500;
        }

        @keyframes blink {
          50% { opacity: 0; }
        }

        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
      </style>
    `;
  }

  renderLive(live) {
    const icon = this.liveIcon(live.state);
    const label = this.liveLabel(live);
    const duration = this.formatDuration(this.liveDuration(live));

    return `
      <div class="live-call">
        <ha-icon class="${this.escape(live.state)}" icon="${icon}"></ha-icon>
        <div class="live-content">
          <div class="label">${label}</div>
          <div class="duration">${duration}</div>
        </div>
      </div>
    `;
  }

  renderHistory(call) {
    const type = call.type || "incoming";
    const duration = Number.isFinite(call.duration) ? ` · ${this.formatDuration(call.duration)}` : "";

    return `
      <div class="history-row">
        <ha-icon class="${this.escape(type)}" icon="${this.historyIcon(type)}"></ha-icon>
        <div class="history-content">
          <div class="label">${this.historyLabel(call)}</div>
          <div class="meta">${this.relativeTime(call.time)}${duration}</div>
        </div>
      </div>
    `;
  }

  liveIcon(state) {
    if (state === "ringing") return "mdi:phone-ring";
    if (state === "dialing") return "mdi:phone-clock";
    return "mdi:phone-in-talk";
  }

  historyIcon(type) {
    if (type === "outgoing") return "mdi:phone-outgoing";
    if (type === "missed") return "mdi:phone-missed";
    if (type === "not_answered") return "mdi:phone-remove";
    return "mdi:phone-incoming";
  }

  liveLabel(live) {
    const texts = this.localize();
    const name = this.escape(live.name || texts.unknown);
    const number = this.escape(live.number || texts.unknown);

    if (live.state === "ringing") return `${texts.ringing}: ${name} (${number})`;
    if (live.state === "dialing") return `${texts.dialing}: ${name} (${number})`;
    return `${texts.talking}: ${name} (${number})`;
  }

  historyLabel(call) {
    const texts = this.localize();
    const name = this.escape(call.name || texts.unknown);
    const number = this.escape(call.number || texts.unknown);

    if (call.type === "outgoing") return `${texts.outgoing} ${name} (${number})`;
    if (call.type === "missed") return `${texts.missed} ${name} (${number})`;
    if (call.type === "not_answered") return `${texts.notAnswered} ${name} (${number})`;
    if (call.type === "incoming") return `${texts.incoming} ${name} (${number})`;
    return this.escape(call.text || "");
  }

  liveDuration(live) {
    if (!live.started_at) {
      return Number(live.duration || 0);
    }
    return Math.max(0, Math.floor(Date.now() / 1000 - Number(live.started_at)));
  }

  formatDuration(seconds) {
    const value = Math.max(0, Number(seconds || 0));
    const hrs = Math.floor(value / 3600);
    const mins = Math.floor((value % 3600) / 60);
    const secs = Math.floor(value % 60);
    if (hrs > 0) {
      return `${hrs}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    }
    return `${mins}:${String(secs).padStart(2, "0")}`;
  }

  relativeTime(timestamp) {
    const texts = this.localize();
    const diff = Math.max(0, Math.floor(Date.now() / 1000 - Number(timestamp || 0)));
    let value;
    if (diff < 60) value = `${diff} ${texts.seconds}`;
    else if (diff < 3600) value = `${Math.floor(diff / 60)} ${texts.minutes}`;
    else if (diff < 86400) value = `${Math.floor(diff / 3600)} ${texts.hours}`;
    else value = `${Math.floor(diff / 86400)} ${texts.days}`;

    return normalizeLanguage(this.config?.language === "auto" ? this._hass?.language : this.config?.language) === "de"
      ? `${texts.before} ${value}`
      : `${value} ${texts.before}`;
  }

  localize() {
    const language = this.config?.language && this.config.language !== "auto"
      ? this.config.language
      : this._hass?.language;
    return TRANSLATIONS[normalizeLanguage(language)];
  }

  escape(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "");
    return div.innerHTML;
  }
}

class FritzboxCalllistCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = {
      entity: DEFAULT_ENTITY,
      max_items: DEFAULT_MAX_ITEMS,
      font_size: DEFAULT_FONT_SIZE,
      language: "auto",
      ...config,
    };
    this.render(true);
  }

  set hass(hass) {
    this._hass = hass;
    this.render(false);
  }

  render(force = false) {
    if (!this.config || !this._hass) {
      return;
    }

    const texts = this.localize();
    const languageKey = normalizeLanguage(this.config?.language === "auto" ? this._hass?.language : this.config?.language);
    const needsForm = force || !this._form || this._languageKey !== languageKey;

    if (needsForm) {
      this.innerHTML = "<ha-form></ha-form>";
      this._form = this.querySelector("ha-form");
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        this.config = event.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this.config },
            bubbles: true,
            composed: true,
          }),
        );
      });
    }

    this._languageKey = languageKey;
    this._form.hass = this._hass;
    this._form.data = this.config;
    this._form.schema = this.schema(texts);
    this._form.computeLabel = (schema) => this.computeLabel(schema, texts);
  }

  schema(texts) {
    return [
      {
        name: "entity",
        required: true,
        selector: { entity: { domain: "sensor" } },
      },
      {
        name: "title",
        selector: { text: {} },
      },
      {
        name: "max_items",
        required: true,
        selector: {
          number: {
            min: 1,
            max: 20,
            mode: "box",
          },
        },
      },
      {
        name: "font_size",
        required: true,
        selector: {
          number: {
            min: 10,
            max: 24,
            mode: "slider",
            unit_of_measurement: "px",
          },
        },
      },
      {
        name: "language",
        selector: {
          select: {
            options: [
              { value: "auto", label: texts.langAuto },
              { value: "de", label: texts.langGerman },
              { value: "en", label: texts.langEnglish },
            ],
            mode: "dropdown",
          },
        },
      },
    ];
  }

  computeLabel(schema, texts) {
    const labels = {
      entity: texts.editorEntity,
      title: texts.editorTitle,
      max_items: texts.editorMaxItems,
      font_size: texts.editorFontSize,
      language: texts.editorLanguage,
    };
    return labels[schema.name] || schema.name;
  }

  localize() {
    return TRANSLATIONS[normalizeLanguage(this.config?.language === "auto" ? this._hass?.language : this.config?.language)];
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, FritzboxCalllistCard);
}

if (!customElements.get(`${CARD_TYPE}-editor`)) {
  customElements.define(`${CARD_TYPE}-editor`, FritzboxCalllistCardEditor);
}

window.customCards = window.customCards || [];

if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
  window.customCards.push({
    type: CARD_TYPE,
    name: "FRITZ!Box Calllist Card",
    description: TRANSLATIONS.en.cardDescription,
    preview: true,
    documentationURL: "https://github.com/RF1705/fritzbox-calllist",
  });
}

console.info(
  "%cFRITZ!Box Calllist Card%c loaded",
  "color: #0288d1; font-weight: 700",
  "color: inherit",
);
})();
