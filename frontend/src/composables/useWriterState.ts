import { ref } from "vue";
import type { CharacterCard, NovelOutline } from "../api/novel";
import type { ProjectSummary } from "../api/project";
import { useAttachment } from "./useAttachment";
import { useDraftStorage } from "./useDraftStorage";

// 模块级单例状态：写作页各组件共享同一份状态，避免引入 Pinia。
const outline = ref<NovelOutline | null>(null);
const text = ref("");
const volumeIndex = ref(0);
const chapterIndex = ref(0);
const cursorPos = ref(0);
const targetLength = ref(800);
const extraReq = ref("");
const loading = ref(false);
const saving = ref(false);
const message = ref("");
const isError = ref(false);
const projectId = ref("");
const projectList = ref<ProjectSummary[]>([]);
const showProjectList = ref(false);
const characterCards = ref<CharacterCard[]>([]);
const viewMode = ref<"chapter" | "cards">("chapter");
const cardVolumeIndex = ref(0);
const generatingCards = ref(false);
const generatingTitle = ref(false);
const memory = ref("");

const storage = useDraftStorage();
const { projectKey, chaptersMap } = storage;

const attachment = useAttachment(
  () => storage.attachKey(volumeIndex.value, chapterIndex.value),
  (msg) => {
    isError.value = !!msg;
    message.value = msg;
  },
);

export function useWriterState() {
  return {
    outline,
    text,
    volumeIndex,
    chapterIndex,
    cursorPos,
    targetLength,
    extraReq,
    loading,
    saving,
    message,
    isError,
    projectId,
    projectList,
    showProjectList,
    characterCards,
    viewMode,
    cardVolumeIndex,
    generatingCards,
    generatingTitle,
    memory,
    storage,
    projectKey,
    chaptersMap,
    attachment: attachment.attachment,
    restoreAttachment: attachment.restore,
    onAttachFile: attachment.onAttachFile,
    removeAttachment: attachment.removeAttachment,
  };
}
