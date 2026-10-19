import { Hero, Section } from '../components/ui'
import mediaData from '../data/media.json'
import { Seo } from '../components/Seo'

type Video = { youtubeId: string; title: string; summary: string }
type Recording = { title: string; summary: string; url: string }

const media = mediaData as { secrets: Video[]; videos: Video[]; audio: Recording[] }

// The site sends Referrer-Policy: same-origin; YouTube refuses to play without a referrer (error 153).
function VideoCard({ video }: { video: Video }) {
  return (
    <li className="rounded-xl border border-brown/10 bg-white overflow-hidden shadow-[0_0_4px_rgba(0,0,0,0.1)]">
      <div className="aspect-video bg-navy/5">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${video.youtubeId}`}
          title={video.title}
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="w-full h-full"
        />
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-navy mb-1">{video.title}</h3>
        {video.summary ? <p className="text-sm text-navy/70 leading-relaxed">{video.summary}</p> : null}
      </div>
    </li>
  )
}

export function MediaPage() {
  return (
    <>
      <Seo title="וידאו והאזנה: בני גל ז״ל וסודות הקואצ'ינג היהודי" description="סדרת סודות הקואצ'ינג היהודי, הרצאות, ועשרה מפגשי אימון מוקלטים של בני גל ז״ל." path="/media" />
      <Hero
        title="וידאו והאזנה"
        subtitle="בני גל ז״ל מלמד את שיטת האימון היהודי: סדרת סודות הקואצ'ינג היהודי, הרצאות, ותהליך אימון מלא מוקלט."
      />

      <Section title="סודות הקואצ'ינג היהודי">
        <ul className="grid gap-6 sm:grid-cols-2 list-none p-0">
          {media.secrets.map((video) => (
            <VideoCard key={video.youtubeId} video={video} />
          ))}
        </ul>
      </Section>

      <Section title="הרצאות וסדנאות" className="bg-white">
        <ul className="grid gap-6 sm:grid-cols-2 list-none p-0">
          {media.videos.map((video) => (
            <VideoCard key={video.youtubeId} video={video} />
          ))}
        </ul>
      </Section>

      <Section title="תהליך אימון מלא: עשרה מפגשים">
        <p className="text-center mb-8">
          הקלטות של תהליך אימון אישי שליווה בני גל, ממפגש ההיכרות ועד המפגש המסכם.
        </p>
        <ol className="space-y-4 list-none p-0">
          {media.audio.map((recording) => (
            <li
              key={recording.url}
              className="rounded-xl border border-brown/10 bg-white p-5 shadow-[0_0_4px_rgba(0,0,0,0.1)]"
            >
              <h3 className="font-semibold text-navy mb-1">{recording.title}</h3>
              <p className="text-sm text-navy/70 leading-relaxed mb-3">{recording.summary}</p>
              <audio controls preload="none" src={recording.url} className="w-full" />
            </li>
          ))}
        </ol>
      </Section>
    </>
  )
}
