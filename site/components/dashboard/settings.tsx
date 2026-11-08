"use client";

import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import type { Settings, SettingsResponse } from "@/lib/dashboard/types";
import { useApi, useCan, useDash } from "./context";
import { Async, PageHead } from "./ui";

type Form = Omit<Settings, "retention_days"> & { retention_days: string };

type BoolKey = "quote_in_alerts" | "auto_delete" | "auto_timeout" | "warn_targets" | "raid_protection" | "quarantine_new_accounts" | "network_share";
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const sorted = (o: Record<string, string>) => Object.entries(o).sort(([a], [b]) => (a < b ? -1 : 1));

function SettingsForm({ d, gid }: { d: SettingsResponse; gid: string }) {
  const { t, call, toast, fail } = useDash();
  const admin = useCan(gid)("admin"); // the API takes settings changes from server admins only
  // Roles deleted from the server since they were given access drop out here, so saving doesn't trip on them.
  const toForm = (s: Settings): Form => ({
    ...s, retention_days: String(s.retention_days),
    dashboard_roles: Object.fromEntries(Object.entries(s.dashboard_roles ?? {}).filter(([id]) => d.roles.some((r) => r.id === id))),
  });
  const [saved, setSaved] = useState<Form>(() => toForm(d.settings));
  const [form, setForm] = useState<Form>(saved);
  const [saving, setSaving] = useState(false);
  const retention = useRef<HTMLInputElement>(null);
  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm((s) => ({ ...s, [k]: v }));

  const parsed = (x: Form): Settings => ({ ...x, retention_days: parseInt(x.retention_days, 10) });
  const diff = () => {
    const cur = parsed(form), orig = parsed(saved), out: Record<string, unknown> = {};
    for (const k of Object.keys(cur) as (keyof Settings)[]) {
      if (k === "minor_role_ids") { if (!same([...cur[k]].sort(), [...orig[k]].sort())) out[k] = cur[k]; }
      else if (k === "dashboard_roles") { if (!same(sorted(cur[k]), sorted(orig[k]))) out[k] = cur[k]; }
      else if (!same(cur[k], orig[k])) out[k] = cur[k];
    }
    return out;
  };
  const dirty = Object.keys(diff()).length > 0;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const dd = diff();
    if ("retention_days" in dd && !((dd.retention_days as number) > 0)) { retention.current?.focus(); return; }
    if (!Object.keys(dd).length) { toast(t("noChanges")); return; }
    setSaving(true);
    try {
      const res = await call<{ settings?: Settings }>("PUT", `/api/guilds/${gid}/settings`, dd);
      const next = toForm({ ...parsed(form), ...(res.settings ?? {}) });
      setSaved(next);
      setForm(next);
      toast(t("saved"));
    } catch (err) {
      fail(err);
    } finally {
      setSaving(false);
    }
  }

  const toggle = (key: BoolKey, help?: string) => (
    <div className="field field-toggle">
      <input type="checkbox" className="switch" id={`s-${key}`} name={key} checked={form[key]} aria-describedby={help ? `d-${key}` : undefined}
        onChange={(e) => set(key, e.target.checked)} />
      <label htmlFor={`s-${key}`}>{t("set_" + key)}</label>
      {help && <p className="help" id={`d-${key}`}>{help}</p>}
    </div>
  );
  const select = (key: "alert_channel_id" | "ping_role_id" | "quarantine_role_id" | "lang", inner: ReactNode) => (
    <div className="field">
      <label htmlFor={`s-${key}`}>{t("set_" + key)}</label>
      <select id={`s-${key}`} name={key} value={form[key] ?? ""} onChange={(e) => set(key, (key === "lang" ? e.target.value : e.target.value || null) as never)}>{inner}</select>
    </div>
  );
  const setAccess = (role: string, level: string) => {
    const next = { ...form.dashboard_roles };
    if (level === "view" || level === "act") next[role] = level;
    else delete next[role];
    set("dashboard_roles", next);
  };
  const none = <option value="">{t("none")}</option>;
  const roleOpts = <>{none}{d.roles.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</>;

  return (
    <form id="settings" className="settings" noValidate onSubmit={submit}>
      {!admin && <p className="view-only" role="note">{t("settingsReadOnly")}</p>}
      <fieldset className="settings-lock" disabled={!admin}>
      <fieldset className="panel"><legend>{t("g_mode")}</legend>
        <div className="mode-pick">
          {(["observe", "protect"] as const).map((mo) => (
            <label key={mo} className="mode-opt">
              <input type="radio" name="mode" value={mo} checked={form.mode === mo} onChange={() => set("mode", mo)} />
              <span className="mode-body"><b>{t("mode_" + mo)}</b><span>{t(`mode_${mo}_d`)}</span></span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="panel"><legend>{t("g_alerts")}</legend>
        {select("alert_channel_id", <>{none}{d.channels.map((x) => <option key={x.id} value={x.id}>#{x.name}</option>)}</>)}
        <div className="field">
          <span className="label" id="l-minlvl">{t("set_alert_min_level")}</span>
          <div className="seg seg-field" role="radiogroup" aria-labelledby="l-minlvl">
            {(["yellow", "red"] as const).map((l) => (
              <label key={l}><input type="radio" name="alert_min_level" value={l} checked={form.alert_min_level === l} onChange={() => set("alert_min_level", l)} /><span>{t("lvlFrom_" + l)}</span></label>
            ))}
          </div>
        </div>
        {select("ping_role_id", roleOpts)}
        {toggle("quote_in_alerts", t("set_quote_in_alerts_d"))}
      </fieldset>
      <fieldset className="panel"><legend>{t("g_auto")}</legend>
        <p className="help help-top">{t("set_auto_d")}</p>
        {toggle("auto_delete")}{toggle("auto_timeout")}{toggle("warn_targets")}
      </fieldset>
      <fieldset className="panel"><legend>{t("g_joins")}</legend>
        {toggle("raid_protection", t("set_raid_protection_d"))}
        {toggle("quarantine_new_accounts")}
        {select("quarantine_role_id", roleOpts)}
      </fieldset>
      <fieldset className="panel"><legend>{t("g_minors")}</legend>
        <div className="field">
          <span className="label" id="l-minor">{t("set_minor_role_ids")}</span>
          <div className="checks" role="group" aria-labelledby="l-minor" aria-describedby="d-minor">
            {d.roles.map((x) => (
              <label key={x.id} className="check">
                <input type="checkbox" name="minor_role_ids" value={x.id} checked={form.minor_role_ids.includes(x.id)}
                  onChange={(e) => set("minor_role_ids", e.target.checked ? [...form.minor_role_ids, x.id] : form.minor_role_ids.filter((r) => r !== x.id))} />
                <span>{x.name}</span>
              </label>
            ))}
          </div>
          <p className="help" id="d-minor">{t("set_minor_role_ids_d")}</p>
        </div>
      </fieldset>
      <fieldset className="panel"><legend>{t("g_network")}</legend>{toggle("network_share")}</fieldset>
      <fieldset className="panel"><legend>{t("g_data")}</legend>
        <div className="field">
          <label htmlFor="s-retention_days">{t("set_retention_days")}</label>
          <div className="input-unit">
            <input type="number" id="s-retention_days" name="retention_days" min="1" step="1" inputMode="numeric" ref={retention}
              value={form.retention_days} onChange={(e) => set("retention_days", e.target.value)} />
            <span>{t("days")}</span>
          </div>
        </div>
        {select("lang", <><option value="en">English</option><option value="sv">Svenska</option></>)}
      </fieldset>
      {admin && (
        <fieldset className="panel"><legend>{t("g_access")}</legend>
          <p className="help help-top" id="d-access">{t("set_access_d")}</p>
          {d.roles.length ? d.roles.map((x) => (
            <div className="field field-access" key={x.id}>
              <label htmlFor={`acc-${x.id}`}>{x.name}</label>
              <select id={`acc-${x.id}`} name={`dashboard_roles.${x.id}`} value={form.dashboard_roles[x.id] ?? ""}
                onChange={(e) => setAccess(x.id, e.target.value)}>
                <option value="">{t("acc_none")}</option>
                <option value="view">{t("acc_view")}</option>
                <option value="act">{t("acc_act")}</option>
              </select>
            </div>
          )) : <p className="help">{t("set_access_none")}</p>}
        </fieldset>
      )}
      </fieldset>
      {admin && <div className="savebar" id="savebar" data-dirty={dirty}>
        <span className="savebar-msg" role="status">{dirty ? t("unsaved") : ""}</span>
        <button type="button" className="btn" onClick={() => setForm(saved)}>{t("reset")}</button>
        <button type="submit" className="btn btn-primary" disabled={saving} aria-busy={saving}>{saving ? t("saving") : t("save")}</button>
      </div>}
    </form>
  );
}

export function SettingsView() {
  const { gid } = useParams<{ gid: string }>();
  const { t } = useDash();
  const res = useApi<SettingsResponse>(`/api/guilds/${gid}/settings`);
  return (
    <>
      <PageHead><h1>{t("settingsTitle")}</h1></PageHead>
      <Async res={res}>{(d) => <SettingsForm d={d} gid={gid} />}</Async>
    </>
  );
}
