// Qualyx Dashboard — Recorded Sessions placeholder.
//
// Not connected to the Backend or Recorder yet. This exists only to make
// the future workflow understandable: recordings captured by the Chrome
// extension will eventually be listed here once Backend upload/storage
// (Claude 2) and the RecordedJourney contract are in place.

function RecordedSessions() {
  return (
    <section data-testid="recorded-sessions" className="max-w-2xl mx-auto px-6 py-10">
      <h2 className="text-lg font-medium mb-3">Recorded Sessions</h2>
      <div
        data-testid="recorded-sessions-empty-state"
        className="border border-dashed border-slate-700 rounded-lg p-8 text-center text-slate-400"
      >
        No recorded sessions yet. Record a journey using the Qualyx Recorder.
      </div>
    </section>
  );
}

export default RecordedSessions;
