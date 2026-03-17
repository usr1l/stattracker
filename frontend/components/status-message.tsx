type StatusMessageProps = {
  title: string;
  body: string;
};

export function StatusMessage({ title, body }: StatusMessageProps) {
  return (
    <div className="panel-surface rounded-[26px] p-8 text-center">
      <p className="eyebrow mb-3">Status</p>
      <h3 className="text-xl font-semibold text-slate-50">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-7 text-slate-400">{body}</p>
    </div>
  );
}
