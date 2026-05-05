import { useEffect, useRef, useState, useCallback, type FormEvent } from 'react';
import { Loader2, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBase } from '../config';

export type PayMePlanPick = {
  id: string;
  price: number;
  currency: string;
  name_he: string;
  name_en: string;
};

type CheckoutConfig = {
  merchant_public_key: string;
  test_mode: boolean;
  checkout_js_url?: string;
};

function ensurePayMeScript(scriptSrc: string): Promise<void> {
  const w = window as unknown as { PayMe?: unknown };
  if (w.PayMe) return Promise.resolve();

  const existing = Array.from(document.getElementsByTagName('script')).find((el) => {
    const s = el as HTMLScriptElement;
    return typeof s.src === 'string' && s.src.includes('hostedfields.js');
  }) as HTMLScriptElement | undefined;

  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('payme-script')), { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = scriptSrc;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('payme-script'));
    document.body.appendChild(s);
  });
}

type Props = {
  open: boolean;
  plan: PayMePlanPick | null;
  getToken: () => Promise<string | null>;
  onClose: () => void;
  onCompleted: () => void;
};

const API_BASE = getApiBase();

export function PayMeCheckoutModal({ open, plan, getToken, onClose, onCompleted }: Props) {
  const { t, i18n } = useTranslation();
  const rtl = i18n.language?.startsWith('he');

  const [busy, setBusy] = useState(false);
  const [bootstrapErr, setBootstrapErr] = useState<string | null>(null);
  const [payErr, setPayErr] = useState<string | null>(null);
  const [config, setConfig] = useState<CheckoutConfig | null>(null);
  const [fieldsReady, setFieldsReady] = useState(false);

  const payMeRef = useRef<{ teardown?: () => void } | null>(null);

  const firstRef = useRef<HTMLInputElement>(null);
  const lastRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const socialRef = useRef<HTMLInputElement>(null);

  const mountCNRef = useRef<HTMLDivElement>(null);
  const mountExpRef = useRef<HTMLDivElement>(null);
  const mountCvvRef = useRef<HTMLDivElement>(null);

  const teardownPayMe = useCallback(() => {
    try {
      payMeRef.current?.teardown?.();
    } catch {
      /* ignore */
    }
    payMeRef.current = null;
  }, []);

  useEffect(() => {
    if (!open) {
      teardownPayMe();
      setBootstrapErr(null);
      setPayErr(null);
      setConfig(null);
      setFieldsReady(false);
    }
  }, [open, teardownPayMe]);

  useEffect(() => {
    if (!open || !plan) return;

    let cancelled = false;
    const run = async () => {
      setBusy(true);
      setBootstrapErr(null);
      setFieldsReady(false);
      teardownPayMe();

      try {
        const jwt = await getToken();
        if (!jwt) throw new Error('auth');

        const cr = await fetch(`${API_BASE}/billing/payme/checkout-config`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        if (!cr.ok) throw new Error('config');

        const cfg = (await cr.json()) as CheckoutConfig;
        if (cancelled) return;

        setConfig(cfg);

        const scriptSrc = cfg.checkout_js_url || 'https://cdn.payme.io/hf/v1/hostedfields.js';
        await ensurePayMeScript(scriptSrc);

        const PayMe = (window as unknown as { PayMe?: any }).PayMe;
        if (!PayMe) throw new Error('no-payme');

        const instance = await PayMe.create(cfg.merchant_public_key, { testMode: cfg.test_mode });
        if (cancelled) return;

        payMeRef.current = instance;

        const hf = instance.hostedFields();
        const stylesBase =
          rtl
            ? { 'font-size': '16px', 'text-align': 'right', color: '#F5F5F0', '::placeholder': { color: '#64748b' } }
            : { 'font-size': '16px', 'text-align': 'left', color: '#F5F5F0', '::placeholder': { color: '#64748b' } };

        const cardNumber = hf.create('cardNumber', { styles: { base: stylesBase } });
        const expiration = hf.create('cardExpiration', { styles: { base: stylesBase } });
        const cvc = hf.create('cvc', { styles: { base: stylesBase } });

        await Promise.all([
          cardNumber.mount(mountCNRef.current),
          expiration.mount(mountExpRef.current),
          cvc.mount(mountCvvRef.current),
        ]);

        if (cancelled) return;
        setFieldsReady(true);
      } catch {
        if (!cancelled) setBootstrapErr(t('billing.paymeLoadFailed'));
      } finally {
        if (!cancelled) setBusy(false);
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional reset when modal opens with plan context
  }, [open, plan?.id]);

  const submitPay = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!plan || !config || !fieldsReady || !(window as unknown as { PayMe?: any }).PayMe) return;

    setPayErr(null);
    setBusy(true);

    try {
      const instance = payMeRef.current as any;
      if (!instance?.tokenize) throw new Error('no-instance');

      const sale = {
        payerFirstName: firstRef.current?.value?.trim() || '',
        payerLastName: lastRef.current?.value?.trim() || '',
        payerEmail: emailRef.current?.value?.trim() || '',
        payerPhone: phoneRef.current?.value?.trim() || '',
        payerSocialId: socialRef.current?.value?.trim() || '',
        total: {
          label: plan.id === 'premium' || plan.id === 'pro' ? (rtl ? plan.name_he : plan.name_en) : plan.name_en,
          amount: {
            currency: plan.currency || 'ILS',
            value: Number(plan.price).toFixed(2),
          },
        },
      };

      const tokenData = await instance.tokenize(sale);
      const token = tokenData?.token as string | undefined;
      if (!token) throw new Error('no-token');

      const jwt = await getToken();
      if (!jwt) throw new Error('auth');

      const subRes = await fetch(`${API_BASE}/billing/payme/subscribe`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${jwt}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          plan: plan.id,
          buyer_token: token,
          payer_first_name: sale.payerFirstName,
          payer_last_name: sale.payerLastName,
          payer_email: sale.payerEmail,
          payer_phone: sale.payerPhone,
          payer_social_id: sale.payerSocialId,
        }),
      });

      const body = await subRes.json().catch(() => ({}));
      if (!subRes.ok) {
        const detail = body?.detail;
        const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : JSON.stringify(detail);
        throw new Error(msg || `pay-${subRes.status}`);
      }

      onCompleted();
      onClose();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setPayErr(msg || t('billing.paymePayError'));
    } finally {
      setBusy(false);
    }
  };

  if (!open || !plan) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div
        className="bg-[#1e293b] rounded-xl border border-white/10 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl"
        dir={rtl ? 'rtl' : 'ltr'}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <h3 className="text-lg font-medium text-[#F5F5F0]" style={{ fontFamily: 'Heebo, sans-serif' }}>
            {t('billing.paymeTitle')}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 text-[#94a3b8]"
            aria-label={t('billing.paymeClose')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={submitPay} className="p-5 space-y-4">
          <p className="text-[#94a3b8] text-sm">{t('billing.paymeSubtitle', { plan: rtl ? plan.name_he : plan.name_en })}</p>

          {bootstrapErr && (
            <div className="rounded-lg bg-red-500/10 text-red-400 text-sm px-3 py-2">{bootstrapErr}</div>
          )}
          {payErr && <div className="rounded-lg bg-red-500/10 text-red-400 text-sm px-3 py-2">{payErr}</div>}

          <div className="grid grid-cols-2 gap-3">
            <input
              ref={firstRef}
              required
              className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/[0.04] text-[#F5F5F0] text-sm"
              placeholder={t('billing.fieldFirstName')}
            />
            <input
              ref={lastRef}
              required
              className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/[0.04] text-[#F5F5F0] text-sm"
              placeholder={t('billing.fieldLastName')}
            />
          </div>
          <input
            ref={emailRef}
            type="email"
            required
            className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/[0.04] text-[#F5F5F0] text-sm"
            placeholder={t('billing.fieldEmail')}
            dir="ltr"
          />
          <input
            ref={phoneRef}
            required
            className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/[0.04] text-[#F5F5F0] text-sm"
            placeholder={t('billing.fieldPhone')}
            dir="ltr"
          />
          <input
            ref={socialRef}
            required
            className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/[0.04] text-[#F5F5F0] text-sm"
            placeholder={t('billing.fieldNationalId')}
            dir="ltr"
          />

          <div className="space-y-2 pt-1">
            <label className="text-xs text-[#94a3b8]">{t('billing.cardNumber')}</label>
            <div ref={mountCNRef} className="min-h-[44px] rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1.5" />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[#94a3b8]">{t('billing.cardExpiry')}</label>
                <div ref={mountExpRef} className="min-h-[44px] rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1.5 mt-1" />
              </div>
              <div>
                <label className="text-xs text-[#94a3b8]">{t('billing.cardCvv')}</label>
                <div ref={mountCvvRef} className="min-h-[44px] rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1.5 mt-1" />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={busy || !!bootstrapErr || !fieldsReady}
            className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {busy ? t('billing.paymeWorking') : t('billing.paymePay', { price: plan.price })}
          </button>
        </form>
      </div>
    </div>
  );
}
