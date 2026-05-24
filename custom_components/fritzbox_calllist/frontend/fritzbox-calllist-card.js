class FritzboxCalllistCard extends HTMLElement {
  static getStubConfig() {
    return {
      entity: "sensor.fritzbox_calllist",
      title: "Telefon",
      max_items: 4,
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please provide a FRITZ!Box Calllist entity.");
    }

    this.config = {
      title: "Telefon",
      max_items: 4,
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

    const liveHtml = isActive ? this.renderLive(live) : "";
    const historyHtml = history.slice(0, limit).map((call) => this.renderHistory(call)).join("");
    const emptyHtml = !isActive && !history.length ? `<div class="empty">Keine Anrufe vorhanden</div>` : "";

    this.innerHTML = `
      <ha-card>
        <div class="card">
          <div class="header">${this.escape(this.config.title)}</div>
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
          padding: 16px;
        }

        .header {
          color: var(--primary-text-color);
          font-size: 18px;
          font-weight: 500;
          line-height: 24px;
          margin-bottom: 12px;
        }

        .live-call,
        .history-row {
          align-items: center;
          color: var(--primary-text-color);
          display: grid;
          gap: 10px;
          grid-template-columns: 28px 1fr auto;
          min-height: 32px;
        }

        .live-call {
          font-weight: 500;
        }

        ha-icon {
          display: inline-flex;
          height: 24px;
          width: 24px;
        }

        .label {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .meta,
        .duration {
          color: #7e7e7e;
          font-size: 12px;
          white-space: nowrap;
        }

        .duration {
          font-variant-numeric: tabular-nums;
        }

        .divider {
          border-top: 1px solid rgba(127, 127, 127, 0.18);
          margin: 12px 0;
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
        <div class="label">${label}</div>
        <div class="duration">${duration}</div>
      </div>
    `;
  }

  renderHistory(call) {
    const type = call.type || "incoming";
    const duration = Number.isFinite(call.duration) ? ` · ${this.formatDuration(call.duration)}` : "";

    return `
      <div class="history-row">
        <ha-icon class="${this.escape(type)}" icon="${this.historyIcon(type)}"></ha-icon>
        <div class="label">${this.escape(call.text || "")}</div>
        <div class="meta">vor ${this.relativeTime(call.time)}${duration}</div>
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
    const name = this.escape(live.name || "Unbekannt");
    const number = this.escape(live.number || "Unbekannt");

    if (live.state === "ringing") return `Anruf von: ${name} (${number})`;
    if (live.state === "dialing") return `Anruf an: ${name} (${number})`;
    return `Gespräch mit: ${name} (${number})`;
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
    const diff = Math.max(0, Math.floor(Date.now() / 1000 - Number(timestamp || 0)));
    if (diff < 60) return `${diff} sekunden`;
    if (diff < 3600) return `${Math.floor(diff / 60)} minuten`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} stunden`;
    return `${Math.floor(diff / 86400)} tagen`;
  }

  escape(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "");
    return div.innerHTML;
  }
}

if (!customElements.get("fritzbox-calllist-card")) {
  customElements.define("fritzbox-calllist-card", FritzboxCalllistCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "fritzbox-calllist-card",
  name: "FRITZ!Box Calllist Card",
  description: "Shows live calls and call history from the FRITZ!Box Calllist integration.",
});
