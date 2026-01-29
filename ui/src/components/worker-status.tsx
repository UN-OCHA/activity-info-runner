import { Button, EntityTitle, H6, Tooltip } from "@blueprintjs/core";
import { useQuery } from "@tanstack/react-query";
import TimeAgo from "react-timeago";
import { API_BASE } from "../utils";

export default function WorkerStatusIndicator() {
  const { data } = useQuery({
    queryKey: ["system"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/system`);
      return (await res.json()) as {
        pollers: {
          identity: string;
          lastAccessTime: string;
        }[];
      };
    },
  });
  return (data?.pollers?.length ?? 0) == 0 ? (
    <Button
      text="Workers offine"
      icon="offline"
      intent="danger"
      variant="minimal"
      size="large"
      disabled
    />
  ) : (
    <Tooltip
      content={
        <div className="flex flex-col justify-start">
          {data?.pollers
            ?.map((p) => p.identity)
            .map((e) => (
              <span key={e}>{e}</span>
            ))}
        </div>
      }
    >
      <EntityTitle
        heading={H6}
        title={`${data?.pollers?.length} worker${(data?.pollers?.length ?? 0) > 1 ? "s" : ""} online`}
        className="leading-3"
        subtitle={
          <>
            <span>Seen </span>
            <TimeAgo
              live={false}
              date={data?.pollers?.[0].lastAccessTime ?? ""}
            />
          </>
        }
        icon="cloud-tick"
      />
    </Tooltip>
  );
}
