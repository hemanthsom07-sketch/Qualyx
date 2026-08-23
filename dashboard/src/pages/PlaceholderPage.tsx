// Generic placeholder page — Stage 1 only wires up routing, not the
// actual pages. Every route below renders this until its real
// implementation stage.

interface PlaceholderPageProps {
  title: string;
  description: string;
}

function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className="max-w-2xl mx-auto px-6 py-10">
      <h2 className="text-lg font-medium mb-3">{title}</h2>
      <div className="border border-dashed border-slate-700 rounded-lg p-8 text-center text-slate-400">
        {description}
      </div>
    </section>
  );
}

export default PlaceholderPage;
