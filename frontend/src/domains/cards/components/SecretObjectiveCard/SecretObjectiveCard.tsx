import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { CardLore } from "@/shared/ui/DetailsCard/CardLore";
import { SecretObjectiveIcon } from "@/shared/ui/SecretObjectiveIcon";

type Props = {
  secretId: string;
};

export function SecretObjectiveCard({ secretId }: Props) {
  const secretData = getSecretObjectiveData(secretId);

  if (!secretData) return null;

  return (
    <DetailsCard width={340} color="red">
      <DetailsCard.Title
        title={secretData.name}
        type="Secret objective"
        meta={[`${secretData.phase} phase`, `${secretData.points} VP`]}
        icon={
          <DetailsCard.Icon
            shape="secret"
            icon={<SecretObjectiveIcon size={30} />}
          />
        }
      />
      <DetailsCard.Section title="Objective" content={secretData.text} />
      <CardLore kind="secretObjective" id={secretId} />
    </DetailsCard>
  );
}
