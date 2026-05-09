export function TypingIndicator() {
  return (
    <div className="flex w-full justify-start">
      <div className="flex items-center gap-1 rounded-lg bg-muted px-3 py-2">
        <Dot delay={0} />
        <Dot delay={150} />
        <Dot delay={300} />
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground"
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}
