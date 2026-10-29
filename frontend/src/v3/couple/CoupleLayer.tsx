import type { Gender } from './coupleApi';
import { inviteLink } from './coupleApi';
import type { useCouple } from './useCouple';
import { CoupleStartScreen } from './CoupleStartScreen';
import { CoupleInviteScreen } from './CoupleInviteScreen';
import { CoupleJoinScreen } from './CoupleJoinScreen';
import { SharePreviewScreen } from './SharePreviewScreen';
import { CoupleWaitingScreen } from './CoupleWaitingScreen';
import { SharedScreen } from './SharedScreen';

interface CoupleLayerProps {
  couple: ReturnType<typeof useCouple>;
  defaultName: string;
  profileGender: Gender | null;
}

/** The couple screen for the current couple view (rendered instead of the regular flow) */
export function CoupleLayer({ couple, defaultName, profileGender }: CoupleLayerProps) {
  const v = couple.view;
  if (!v) return null;
  const myGender = couple.status?.me.gender ?? profileGender;
  switch (v.kind) {
    case 'start':
      return (
        <CoupleStartScreen defaultName={defaultName} profileGender={profileGender} busy={couple.busy} error={couple.error}
          onSubmit={couple.start} onBack={couple.close} />
      );
    case 'invite':
      return (
        <CoupleInviteScreen title={v.title} link={inviteLink(v.token)} myName={v.name} myGender={v.gender}
          onBegin={() => couple.beginMyPart(v.conversationId, v.sessionId, v.title)} />
      );
    case 'join':
      return (
        <CoupleJoinScreen preview={v.preview} defaultName={defaultName} profileGender={profileGender} busy={couple.busy}
          error={couple.error} onJoin={couple.join} onContinueJoined={couple.continueJoined} onDismiss={couple.dismissJoin} />
      );
    case 'preview':
      return (
        <SharePreviewScreen key={v.checkpoint} checkpoint={v.checkpoint} lines={v.lines}
          partnerName={couple.status?.partner?.name ?? null} partnerGender={couple.status?.partner?.gender ?? null}
          myGender={myGender} busy={couple.busy} error={couple.error} onApprove={couple.approve} />
      );
    case 'waiting':
      return (
        <CoupleWaitingScreen checkpoint={v.checkpoint} status={couple.status} remind={couple.remind}
          onPrepareRemind={couple.prepareRemind} onCancel={couple.cancel} onContinueAlone={() => couple.afterShared(v.checkpoint)} />
      );
    case 'shared':
      return <SharedScreen checkpoint={v.checkpoint} data={v.data} onContinue={() => couple.afterShared(v.checkpoint)} />;
  }
}
