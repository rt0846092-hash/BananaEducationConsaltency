import { Link } from "react-router-dom";
import { OFFICE } from "../config";
import { usePageMeta } from "../seo";

/**
 * A plain-language privacy page, linked from the consent checkbox on the form.
 *
 * THIS IS A TEMPLATE. Before a real client goes live:
 *   1. Replace every [bracketed] part with the client's real details.
 *   2. Have it read by someone who knows the privacy law where the client
 *      operates (in Nepal, the Individual Privacy Act, 2075).
 *   3. Delete the yellow notice below.
 * It describes what this software actually does, so if you change how data
 * is handled, change this page too.
 */

const UPDATED = "[date you publish this page]";

function Section({ title, children }) {
  return (
    <section className="mt-10">
      <h2 className="text-xl">{title}</h2>
      <div className="mt-3 space-y-3 leading-relaxed text-navy">{children}</div>
    </section>
  );
}

export default function Privacy() {
  usePageMeta({ title: "Privacy: how we use your details",
                description: "What we collect when you ask for counselling, who can see it, and how to have it deleted." });
  return (
    <div className="wrap max-w-prose py-14">
      <div className="rounded-md border border-urgent/40 bg-urgent/5 p-4 text-sm text-urgent">
        Template. Replace the [bracketed] parts and have this page checked before real
        students use the site. Then remove this notice from <code>src/pages/Privacy.jsx</code>.
      </div>

      <h1 className="mt-8 text-3xl">How we use your details</h1>
      <p className="mt-2 text-sm text-navy-soft">Last updated {UPDATED}</p>

      <p className="mt-6 leading-relaxed text-navy">
        {OFFICE.name} ([registered company name and registration number], [address]) helps
        students apply to universities abroad. This page explains what we collect when you
        contact us, why, and what you can ask us to do with it.
      </p>

      <Section title="What we collect">
        <p>
          From the counselling form: your name, phone number, email if you give it, and the
          countries you're interested in. If you answer the optional questions, also your
          qualification, test scores, budget, study gap and whether you have applied for a
          student visa before.
        </p>
        <p>
          If you become a student with us, we may also keep copies of documents you give us,
          such as your passport, transcripts, test reports, bank statements and statement of
          purpose.
        </p>
      </Section>

      <Section title="Why we collect it">
        <p>
          To call you back, give you advice that fits your situation, and — if you decide to
          go ahead — prepare and track your university and visa applications. We do not use
          it for anything else.
        </p>
      </Section>

      <Section title="Who can see it">
        <p>
          Only the counsellor handling your case and the office manager. Counsellors cannot
          see other counsellors' students. Downloading the full student list is limited to
          the office manager, and every download is recorded.
        </p>
        <p>
          We send your details to a university, embassy or test provider only when that is
          part of an application you have agreed to. We never sell your details or give them
          to anyone for marketing.
        </p>
        <p>
          Our website and database are hosted by [hosting providers, e.g. Render and Vercel],
          and uploaded documents are stored with [storage provider]. [Say where the data is
          physically stored if you know.]
        </p>
      </Section>

      <Section title="How long we keep it">
        <p>
          [For example: If you don't become a student, we delete your enquiry after
          [24 months]. If you do, we keep your file for [number] years after your case
          closes, because [reason — e.g. university or legal requirements].]
        </p>
      </Section>

      <Section title="Your choices">
        <p>You can ask us at any time to:</p>
        <ul className="list-disc space-y-1.5 pl-6">
          <li>show you what we hold about you,</li>
          <li>correct anything that's wrong,</li>
          <li>stop contacting you, or</li>
          <li>delete your details, unless we have to keep them for an application in progress.</li>
        </ul>
        <p>
          Call {OFFICE.phone}, email{" "}
          <a href={`mailto:${OFFICE.email}`} className="text-grass underline">{OFFICE.email}</a>,
          or visit the office. [Name or role of the person responsible] will reply within
          [number] working days.
        </p>
      </Section>

      <Section title="Questions">
        <p>
          If you're unhappy with how we handled your information, contact us first. [If the
          law in your country gives people a regulator to complain to, name it here.]
        </p>
      </Section>

      <Link to="/apply" className="btn-go mt-12">Back to the form</Link>
    </div>
  );
}
