import { GlossaryText } from "@/components/GlossaryText";
import type { ActionItem } from "@/lib/checklist";

interface ActionChecklistProps {
  items: ActionItem[];
}

export function ActionChecklist({ items }: ActionChecklistProps) {
  if (items.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">What to do</h2>
      <ul className="flex flex-col gap-2">
        {items.map((item, index) => (
          <li
            key={index}
            className="flex items-start gap-2 rounded-lg border border-neutral-200 px-3 py-2 dark:border-neutral-800"
          >
            <span
              className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border border-neutral-300 dark:border-neutral-700"
              aria-hidden="true"
            />
            <div className="flex flex-1 flex-col gap-0.5">
              <span className="text-sm text-neutral-800 dark:text-neutral-200">
                <GlossaryText text={item.action} />
              </span>
              {item.deadline && (
                <span
                  className={
                    item.urgent
                      ? "text-xs font-medium text-red-600 dark:text-red-400"
                      : "text-xs text-neutral-500 dark:text-neutral-500"
                  }
                >
                  {item.urgent ? "⚠ Urgent — " : ""}Due {item.deadline}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
