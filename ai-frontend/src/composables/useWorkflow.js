import { computed, reactive } from 'vue'

/**
 * 临床工作流状态机：病情描述 → 医师确认评估 → 推荐候选 → 处方版本 → 审核任务。
 * 只保存业务编号与状态用于跨步骤衔接；所有事实以 medical-service-backend 返回为准。
 *
 * 步骤推进语义：
 *   intake.status     awaiting_confirmation → confirmed
 *   assessment        确认后产生 assessment_no / context_version，推荐步骤依赖它
 *   recommendation    requested → candidates_ready → decided
 *   prescription      draft → submitted → approved/rejected
 *   reviewTask        created → system_reviewed → approved/intervention_required/rejected/superseded
 */

const state = reactive({
  activeStep: 'intake', // intake | recommendation | prescription | review
  // 病情描述与确认
  intakeNo: '',
  intakeStatus: '',
  emergencyTriggered: false,
  assessmentNo: '',
  contextVersion: '',
  // 推荐
  recommendationNo: '',
  recommendationStatus: '',
  // 处方与审核
  prescriptionNo: '',
  prescriptionStatus: '',
  currentVersionNo: 0,
  reviewTaskNo: '',
  reviewTaskStatus: '',
})

export function useWorkflow() {
  const workflow = state

  const canRecommend = computed(() => Boolean(state.assessmentNo))
  const canPrescribe = computed(() => true) // 也可不经推荐直接开方
  const canReview = computed(() => Boolean(state.prescriptionNo || state.reviewTaskNo))

  function startIntake(no, status, emergency) {
    state.intakeNo = no
    state.intakeStatus = status
    state.emergencyTriggered = emergency === 'triggered'
  }

  function applyAssessment(assessment) {
    state.assessmentNo = assessment.assessment_id
    state.contextVersion = assessment.context_version
    state.intakeStatus = 'confirmed'
    state.emergencyTriggered = false
  }

  function applyRecommendation(data) {
    state.recommendationNo = data.recommendation_id
    state.recommendationStatus = data.status
  }

  function applyPrescription(data) {
    state.prescriptionNo = data.prescription_id
    state.prescriptionStatus = data.status
    state.currentVersionNo = data.current_version_no
  }

  function applyReviewTask(taskData) {
    state.reviewTaskNo = taskData.review_task_id
    state.reviewTaskStatus = taskData.status
  }

  function switchStep(step) {
    state.activeStep = step
  }

  return {
    workflow: state,
    canRecommend,
    canPrescribe,
    canReview,
    startIntake,
    applyAssessment,
    applyRecommendation,
    applyPrescription,
    applyReviewTask,
    switchStep,
  }
}
