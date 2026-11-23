import { Box, Text } from "@/ds";
import { StatusInfo } from "@/shared/ui/StatusInfo/StatusInfo";
import styles from "./TyrantToken.module.css";

export function TyrantToken() {
  return (
    <StatusInfo status="tyrant">
      <Box p={6} px={8} className={styles.root}>
        <Text ff="heading" c="yellow.6" size="sm" fw={700}>
          TYRANT
        </Text>
      </Box>
    </StatusInfo>
  );
}
