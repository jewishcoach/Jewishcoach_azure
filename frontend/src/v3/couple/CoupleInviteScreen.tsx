import { useState } from 'react';
import { Copy, MessageCircle, Share2 } from 'lucide-react';
import type { Gender } from './coupleApi';
import { gFor, inviteMessage } from './lines';
import { CoupleScreen, Note, Panel, PrimaryButton, ScreenTitle, SecondaryButton } from './ui';

interface CoupleInviteScreenProps {
  title: string;
  link: string;
  myName: string;
  myGender: Gender | null;
  onBegin: () => void;
}

/** The one-time link for the partner: WhatsApp, the phone's share sheet, or copy */
export function ShareLinkButtons({ text, link }: { text: string; link: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex flex-wrap items-center justify-center gap-3">
      <SecondaryButton onClick={() => window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')}>
        <MessageCircle size={16} className="text-[#01897b]" />
        <span>שליחה בוואטסאפ</span>
      </SecondaryButton>
      {typeof navigator.share === 'function' && (
        <SecondaryButton onClick={() => { navigator.share({ text }).catch(() => {}); }}>
          <Share2 size={16} className="text-[#01897b]" />
          <span>שיתוף</span>
        </SecondaryButton>
      )}
      <SecondaryButton
        onClick={() => {
          navigator.clipboard?.writeText(link).then(() => setCopied(true)).catch(() => {});
        }}
      >
        <Copy size={16} className="text-[#01897b]" />
        <span>{copied ? 'הקישור הועתק ✓' : 'העתקת הקישור'}</span>
      </SecondaryButton>
    </div>
  );
}

export function CoupleInviteScreen({ title, link, myName, myGender, onBegin }: CoupleInviteScreenProps) {
  const g = gFor(myGender);
  return (
    <CoupleScreen>
      <ScreenTitle sub={`״${title}״`}>הקישור מוכן</ScreenTitle>
      <Panel className="space-y-4">
        <Note>{`${g('שלח', 'שלחי')} אותו לבן/בת הזוג. הקישור אישי, לשימוש אחד, ובתוקף 14 יום.`}</Note>
        <ShareLinkButtons text={inviteMessage(myName, myGender, title, link)} link={link} />
      </Panel>
      <Note>{`${g('אתה יכול', 'את יכולה')} להתחיל את החלק שלך כבר עכשיו — לא צריך לחכות.`}</Note>
      <div className="flex justify-center">
        <PrimaryButton onClick={onBegin}>להתחיל את החלק שלי</PrimaryButton>
      </div>
    </CoupleScreen>
  );
}
