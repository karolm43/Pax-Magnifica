import { Button, Group, Select, Stack, Text } from "@/ds";
import { IconX } from "@tabler/icons-react";
import type { CardOption } from "./cardOptions";

type Props = {
  /** Aktualne id kart (w kolejności). */
  ids: string[];
  /** Opcje do dodania (nazwa → id). */
  options: CardOption[];
  /** Nazwa karty do pokazania na chipie (fallback: samo id). */
  labelFor: (id: string) => string;
  placeholder: string;
  emptyLabel: string;
  disabled?: boolean;
  onAdd: (id: string) => void;
  onRemove: (id: string) => void;
};

/**
 * Lista kart z dodawaniem (Select z wyszukiwaniem) i usuwaniem (chip z „×").
 * Wspólny wzorzec dla ręki (karty akcji / tajne cele / weksle) i stref gracza —
 * żeby edytor God-Mode miał jeden, spójny sposób edycji kolekcji kart.
 */
export function CardListEditor({
  ids,
  options,
  labelFor,
  placeholder,
  emptyLabel,
  disabled = false,
  onAdd,
  onRemove,
}: Props) {
  return (
    <Stack gap={6}>
      <Select
        size="xs"
        placeholder={placeholder}
        data={options}
        value={null}
        onChange={(v) => {
          if (v) onAdd(v);
        }}
        searchable
        clearable
        disabled={disabled}
      />
      <Group gap={6} wrap="wrap">
        {ids.map((id) => (
          <Button
            key={id}
            size="xs"
            variant="default"
            rightSection={<IconX size={11} />}
            disabled={disabled}
            onClick={() => onRemove(id)}
            title="Remove"
          >
            {labelFor(id)}
          </Button>
        ))}
        {ids.length === 0 && (
          <Text size="xs" c="dimmed">
            {emptyLabel}
          </Text>
        )}
      </Group>
    </Stack>
  );
}
