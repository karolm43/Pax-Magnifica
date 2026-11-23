import { Box, Text } from "@/ds";
import { StatusInfo } from "@/shared/ui/StatusInfo/StatusInfo";
import styles from "./SpeakerToken.module.css";

export function SpeakerToken() {
  return (
    <StatusInfo status="speaker">
      <Box className={styles.root}>
        <Text ff="heading" size="xs" fw={700} className={styles.label}>
          SPEAKER
        </Text>
      </Box>
    </StatusInfo>
  );
}
