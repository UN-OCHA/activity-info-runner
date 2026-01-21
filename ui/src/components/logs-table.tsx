import { Card, CardList } from "@blueprintjs/core";

export default function LogsTable({ logs }: { logs: string[] }) {
  return (
    <CardList compact className="h-full overflow-y-auto mb-12">
      {logs.map((log, i) => (
        <Card key={i} className="text-xs min-h-0!">
          <span>{log}</span>
        </Card>
      ))}
    </CardList>
  );
}
