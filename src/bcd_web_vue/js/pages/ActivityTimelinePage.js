// @ts-check

const { defineComponent, computed, onBeforeUnmount, onMounted, ref, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../api/client.js';
import { formatDateTime, formatTime } from '../utils/date.js';
import { groupTimelineActions } from '../utils/activityTimeline.js';

const SVG_WIDTH = 1200;
const AXIS_LEFT = 56;
const AXIS_RIGHT = SVG_WIDTH - 28;
const REFRESH_INTERVAL_MS = 15000;
const ZOOM_LEVELS = [1, 2, 4, 6, 8, 12, 24];

/**
 * @typedef {Object} CirculationAction
 * @property {string} id
 * @property {number} transaction_id
 * @property {'checkout'|'return'} action
 * @property {string} occurred_at
 * @property {string} borrower_id
 * @property {string} borrower_name
 * @property {number|null} class_id
 * @property {string|null} class_name
 * @property {string|null} homeroom_teacher
 * @property {string} item_id
 * @property {string} title
 */

/**
 * @typedef {Object} TimelineGroup
 * @property {string} id
 * @property {number|null} classId
 * @property {string|null} className
 * @property {string|null} homeroomTeacher
 * @property {string} startAt
 * @property {string} endAt
 * @property {CirculationAction[]} actions
 * @property {{borrowerId: string, borrowerName: string, checkouts: CirculationAction[], returns: CirculationAction[]}[]} students
 * @property {number} checkoutCount
 * @property {number} returnCount
 */

/**
 * @typedef {Object} ActivityDay
 * @property {string} activity_date
 * @property {number} checkout_count
 * @property {number} return_count
 * @property {string} first_action_at
 * @property {string} last_action_at
 */

/**
 * @param {Date} date
 * @returns {string}
 */
function toLocalDateTimeInput(date) {
    const pad = (/** @type {number} */ value) => String(value).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * @param {Date} date
 * @returns {string}
 */
function toLocalApiDateTime(date) {
    return `${toLocalDateTimeInput(date)}:${String(date.getSeconds()).padStart(2, '0')}`;
}

/**
 * @param {number} durationHours
 * @returns {Date}
 */
function getLiveRangeStart(durationHours) {
    return new Date(Date.now() - durationHours * 60 * 60 * 1000);
}

/**
 * @param {string} value
 * @returns {Date}
 */
function localStartOfDay(value) {
    return new Date(`${value}T00:00:00`);
}

export default defineComponent({
    name: 'ActivityTimelinePage',

    setup() {
        const { t, locale } = useI18n();
        const actions = ref(/** @type {CirculationAction[]} */ ([]));
        const activityDays = ref(/** @type {ActivityDay[]} */ ([]));
        const loading = ref(true);
        const loadError = ref(false);
        const activityDaysLoading = ref(false);
        const activityDaysError = ref(false);
        const classFilter = ref('');
        const liveMode = ref(true);
        const durationHours = ref(4);
        const rangeStart = ref(getLiveRangeStart(durationHours.value));
        const rangeStartInput = computed(() => toLocalDateTimeInput(rangeStart.value));
        const selectedActivityDay = computed(() => {
            const date = rangeStart.value;
            const dateKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            return activityDays.value.some(day => day.activity_date === dateKey) ? dateKey : '';
        });
        const selectedGroupId = ref(/** @type {string|null} */ (null));
        const followLatest = ref(true);
        const lastUpdatedAt = ref(/** @type {Date|null} */ (null));
        let refreshTimer = 0;
        let requestVersion = 0;
        let activityDaysRequestVersion = 0;
        /** @type {{startX: number, startTime: number, pointerId: number, moved: boolean}|null} */
        let activePan = null;

        const rangeEnd = computed(() =>
            new Date(rangeStart.value.getTime() + durationHours.value * 60 * 60 * 1000)
        );
        /** @param {'students'|'returnCount'|'checkoutCount'} key @param {number} count */
        const pluralText = (key, count) =>
            t(`activityTimeline.${key}_${count === 1 ? 'one' : 'other'}`, { count });
        const filteredActions = computed(() => {
            if (!classFilter.value) return actions.value;
            return actions.value.filter(action =>
                String(action.class_id ?? 'none') === classFilter.value
            );
        });
        const groups = computed(() =>
            groupTimelineActions(filteredActions.value)
        );
        const latestGroup = computed(() => groups.value.reduce(
            /** @param {TimelineGroup|null} latest @param {TimelineGroup} group */
            (latest, group) =>
                !latest || Date.parse(group.endAt) > Date.parse(latest.endAt) ? group : latest,
            null
        ));
        const selectedGroup = computed(() =>
            groups.value.find(group => group.id === selectedGroupId.value) || latestGroup.value
        );
        const classes = computed(() => {
            const unique = new Map();
            for (const action of actions.value) {
                const id = String(action.class_id ?? 'none');
                if (!unique.has(id)) {
                    unique.set(id, {
                        id,
                        name: action.class_name || t('activityTimeline.noClass'),
                        teacher: action.homeroom_teacher || ''
                    });
                }
            }
            return [...unique.values()].sort((left, right) => left.name.localeCompare(right.name));
        });
        /** @param {string} timestamp */
        const timeToX = timestamp => {
            const elapsed = Date.parse(timestamp) - rangeStart.value.getTime();
            const ratio = elapsed / (durationHours.value * 60 * 60 * 1000);
            return AXIS_LEFT + ratio * (AXIS_RIGHT - AXIS_LEFT);
        };
        const timelineGroups = computed(() => {
            /** @type {{group: TimelineGroup, x1: number, x2: number, center: number, label: string, width: number, lane: number, y: number}[]} */
            const positioned = [];
            /** @type {number[]} */
            const laneEnds = [];
            const ordered = [...groups.value].sort((left, right) =>
                Date.parse(left.startAt) - Date.parse(right.startAt)
            );

            for (const group of ordered) {
                const x1 = timeToX(group.startAt);
                const x2 = timeToX(group.endAt);
                const label = [
                    group.className || t('activityTimeline.noClass'),
                    group.homeroomTeacher,
                    pluralText('students', group.students.length)
                ].filter(Boolean).join(' · ');
                const width = Math.min(340, Math.max(150, label.length * 7 + 24));
                const center = Math.min(
                    AXIS_RIGHT - width / 2,
                    Math.max(AXIS_LEFT + width / 2, (x1 + x2) / 2)
                );
                const labelLeft = center - width / 2;
                let lane = laneEnds.findIndex(end => end + 10 < labelLeft);
                if (lane < 0) lane = laneEnds.length;
                laneEnds[lane] = center + width / 2;
                positioned.push({
                    group,
                    x1,
                    x2: Math.max(x1 + 8, x2),
                    center,
                    label,
                    width,
                    lane,
                    y: 22 + lane * 30
                });
            }
            return positioned;
        });
        const axisY = computed(() => 44 + Math.max(1, ...timelineGroups.value.map(group => group.lane + 1)) * 30);
        const timelineHeight = computed(() => axisY.value + 64);
        const ticks = computed(() => {
            const stepHours = durationHours.value <= 2
                ? 0.25
                : durationHours.value <= 4
                    ? 0.5
                    : durationHours.value <= 8
                        ? 1
                        : durationHours.value <= 12
                            ? 2
                            : 4;
            const count = Math.floor(durationHours.value / stepHours);
            return Array.from({ length: count + 1 }, (_, index) => {
                const date = new Date(rangeStart.value.getTime() + index * stepHours * 60 * 60 * 1000);
                const ratio = index * stepHours / durationHours.value;
                return {
                    x: AXIS_LEFT + ratio * (AXIS_RIGHT - AXIS_LEFT),
                    label: formatTime(date, locale.value),
                    dateLabel: index === 0 || date.getHours() === 0
                        ? new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'short' }).format(date)
                        : ''
                };
            });
        });
        const timelineEvents = computed(() => {
            const events = filteredActions.value
                .map(action => ({
                    action,
                    groupId: groups.value.find(group => group.actions.some(item => item.id === action.id))?.id || ''
                }))
                .sort((left, right) => Date.parse(left.action.occurred_at) - Date.parse(right.action.occurred_at));
            /** @type {Map<string, {action: CirculationAction, groupId: string, actionCount: number}>} */
            const markers = new Map();
            for (const event of events) {
                const timestamp = Date.parse(event.action.occurred_at);
                const key = `${timestamp}:${event.groupId}:${event.action.action}`;
                const marker = markers.get(key);
                if (marker) {
                    marker.actionCount += 1;
                } else {
                    markers.set(key, { ...event, actionCount: 1 });
                }
            }

            return [...markers.values()].map(marker => ({
                ...marker,
                x: timeToX(marker.action.occurred_at),
                strokeWidth: Math.min(11, 3 + (marker.actionCount - 1) * 2)
            }));
        });
        const isLatestSelected = computed(() =>
            !selectedGroup.value || selectedGroup.value.id === latestGroup.value?.id
        );
        const lastUpdatedLabel = computed(() =>
            lastUpdatedAt.value ? formatTime(lastUpdatedAt.value, locale.value) : ''
        );
        /** @param {ActivityDay} day */
        const formatActivityDay = day => {
            const date = localStartOfDay(day.activity_date);
            const label = new Intl.DateTimeFormat(locale.value, {
                weekday: 'short',
                day: 'numeric',
                month: 'short',
                year: 'numeric'
            }).format(date);
            return `${label} · ${pluralText('checkoutCount', day.checkout_count)} · ${pluralText('returnCount', day.return_count)}`;
        };

        const syncFollowLatest = () => {
            if (followLatest.value || !groups.value.some(group => group.id === selectedGroupId.value)) {
                selectedGroupId.value = latestGroup.value?.id || null;
                followLatest.value = true;
            }
        };

        const loadActions = async () => {
            const currentRequest = ++requestVersion;
            if (liveMode.value) {
                rangeStart.value = getLiveRangeStart(durationHours.value);
            }
            loadError.value = false;
            try {
                const result = await apiClient.get(
                    '/circulation/actions',
                    {
                        start: toLocalApiDateTime(rangeStart.value),
                        end: toLocalApiDateTime(rangeEnd.value)
                    },
                    { skipGlobalLoading: true }
                );
                if (currentRequest !== requestVersion) return;
                if (!Array.isArray(result)) {
                    throw new Error('The circulation actions response must be an array');
                }
                actions.value = result;
                lastUpdatedAt.value = new Date();
                syncFollowLatest();
            } catch (error) {
                if (currentRequest === requestVersion) {
                    console.error('Error loading the activity timeline:', error);
                    loadError.value = true;
                }
            } finally {
                if (currentRequest === requestVersion) loading.value = false;
            }
        };

        const loadActivityDays = async () => {
            const currentRequest = ++activityDaysRequestVersion;
            const params = /** @type {{class_id?: number, no_class?: boolean}} */ ({});
            if (classFilter.value === 'none') {
                params.no_class = true;
            } else if (classFilter.value) {
                params.class_id = Number(classFilter.value);
            }
            activityDaysLoading.value = true;
            activityDaysError.value = false;
            try {
                const result = await apiClient.get(
                    '/circulation/activity-days',
                    params,
                    { skipGlobalLoading: true }
                );
                if (currentRequest !== activityDaysRequestVersion) return;
                if (
                    !Array.isArray(result) ||
                    result.some(day =>
                        typeof day.activity_date !== 'string' ||
                        typeof day.checkout_count !== 'number' ||
                        typeof day.return_count !== 'number' ||
                        typeof day.first_action_at !== 'string' ||
                        typeof day.last_action_at !== 'string' ||
                        Number.isNaN(Date.parse(day.first_action_at)) ||
                        Number.isNaN(Date.parse(day.last_action_at)) ||
                        Date.parse(day.first_action_at) > Date.parse(day.last_action_at)
                    )
                ) {
                    throw new Error('The circulation activity days response is invalid');
                }
                activityDays.value = result;
            } catch (error) {
                if (currentRequest === activityDaysRequestVersion) {
                    console.error('Error loading circulation activity days:', error);
                    activityDaysError.value = true;
                }
            } finally {
                if (currentRequest === activityDaysRequestVersion) {
                    activityDaysLoading.value = false;
                }
            }
        };

        /** @param {Event} event */
        const selectActivityDay = event => {
            if (!(event.target instanceof HTMLSelectElement)) return;
            const selectedDate = event.target.value;
            const day = activityDays.value.find(
                entry => entry.activity_date === selectedDate
            );
            if (!day) return;
            const firstAction = Date.parse(day.first_action_at);
            const lastAction = Date.parse(day.last_action_at);
            const requiredHours = (lastAction - firstAction) / (60 * 60 * 1000) + 0.5;
            const duration = ZOOM_LEVELS.find(hours => hours >= requiredHours)
                || ZOOM_LEVELS[ZOOM_LEVELS.length - 1];
            const center = (firstAction + lastAction) / 2;
            const dayStart = localStartOfDay(day.activity_date).getTime();
            const dayEnd = dayStart + 24 * 60 * 60 * 1000;
            const start = Math.max(
                dayStart,
                Math.min(
                    center - duration * 30 * 60 * 1000,
                    dayEnd - duration * 60 * 60 * 1000
                )
            );
            liveMode.value = false;
            followLatest.value = true;
            durationHours.value = duration;
            rangeStart.value = new Date(start);
            selectedGroupId.value = null;
            loadActions();
        };

        const refreshTimeline = () => {
            loadActions();
            loadActivityDays();
        };

        /** @param {-1|1} direction */
        const shiftWindow = direction => {
            liveMode.value = false;
            rangeStart.value = new Date(
                rangeStart.value.getTime() + direction * durationHours.value * 60 * 60 * 1000
            );
            if (direction > 0 && rangeEnd.value >= new Date()) {
                liveMode.value = true;
            }
            loadActions();
        };

        const jumpToNow = () => {
            liveMode.value = true;
            followLatest.value = true;
            rangeStart.value = getLiveRangeStart(durationHours.value);
            selectedGroupId.value = null;
            loadActions();
        };

        /** @param {Event} event */
        const setRangeStart = event => {
            if (!(event.target instanceof HTMLInputElement)) return;
            const value = event.target.value;
            const parsed = value ? new Date(value) : null;
            if (!parsed || Number.isNaN(parsed.getTime())) return;
            liveMode.value = false;
            rangeStart.value = parsed;
            loadActions();
        };

        /** @param {-1|1} direction */
        const zoom = direction => {
            const currentIndex = ZOOM_LEVELS.indexOf(durationHours.value);
            const nextIndex = Math.max(0, Math.min(ZOOM_LEVELS.length - 1, currentIndex + direction));
            if (nextIndex === currentIndex) return;
            const nextDuration = ZOOM_LEVELS[nextIndex];
            if (liveMode.value) {
                rangeStart.value = getLiveRangeStart(nextDuration);
            } else {
                const center = rangeStart.value.getTime() + durationHours.value * 30 * 60 * 1000;
                rangeStart.value = new Date(center - nextDuration * 30 * 60 * 1000);
            }
            durationHours.value = nextDuration;
            loadActions();
        };

        /** @param {string} groupId */
        const selectGroup = groupId => {
            selectedGroupId.value = groupId;
            followLatest.value = groupId === latestGroup.value?.id;
            if (!followLatest.value) liveMode.value = false;
        };

        const followLatestGroup = () => {
            followLatest.value = true;
            selectedGroupId.value = latestGroup.value?.id || null;
            if (!liveMode.value) jumpToNow();
        };

        watch(classFilter, loadActivityDays);

        /** @param {PointerEvent} event */
        const beginPan = event => {
            if (
                event.button !== 0 ||
                (event.target instanceof Element && event.target.closest('[role="button"]'))
            ) return;
            activePan = {
                startX: event.clientX,
                startTime: rangeStart.value.getTime(),
                pointerId: event.pointerId,
                moved: false
            };
            if (event.currentTarget instanceof SVGSVGElement) {
                event.currentTarget.setPointerCapture(event.pointerId);
            }
        };

        /** @param {PointerEvent} event */
        const movePan = event => {
            if (!activePan || activePan.pointerId !== event.pointerId) return;
            const deltaX = event.clientX - activePan.startX;
            if (Math.abs(deltaX) > 3) {
                activePan.moved = true;
                liveMode.value = false;
            }
            if (!activePan.moved) return;
            if (!(event.currentTarget instanceof SVGSVGElement)) return;
            const width = event.currentTarget.getBoundingClientRect().width
                * (AXIS_RIGHT - AXIS_LEFT) / SVG_WIDTH;
            if (!width) return;
            const deltaMs = -deltaX / width * durationHours.value * 60 * 60 * 1000;
            rangeStart.value = new Date(activePan.startTime + deltaMs);
        };

        /** @param {PointerEvent} event */
        const endPan = event => {
            if (!activePan || activePan.pointerId !== event.pointerId) return;
            const moved = activePan.moved;
            activePan = null;
            if (moved) loadActions();
        };

        /** @param {CirculationAction} action */
        /** @param {CirculationAction} action @param {number} [actionCount=1] */
        const actionTooltip = (action, actionCount = 1) => {
            const details = t('activityTimeline.actionTooltip', {
            action: t(`activityTimeline.${action.action}`),
            time: formatDateTime(action.occurred_at, locale.value),
            student: action.borrower_name,
            title: action.title
            });
            return actionCount > 1
                ? `${details} · ${t('activityTimeline.actionsAtSameTime', { count: actionCount })}`
                : details;
        };

        onMounted(() => {
            loadActions();
            loadActivityDays();
            refreshTimer = window.setInterval(loadActions, REFRESH_INTERVAL_MS);
        });

        onBeforeUnmount(() => {
            window.clearInterval(refreshTimer);
            requestVersion += 1;
            activityDaysRequestVersion += 1;
        });

        return {
            t,
            locale,
            actions,
            activityDays,
            activityDaysLoading,
            activityDaysError,
            classes,
            classFilter,
            loading,
            loadError,
            lastUpdatedLabel,
            liveMode,
            durationHours,
            rangeStart,
            rangeStartInput,
            rangeEnd,
            selectedActivityDay,
            selectedGroup,
            latestGroup,
            isLatestSelected,
            timelineGroups,
            timelineEvents,
            ticks,
            axisY,
            timelineHeight,
            formatTime: (/** @type {string|Date} */ timestamp) => formatTime(timestamp, locale.value),
            pluralText,
            actionTooltip,
            beginPan,
            movePan,
            endPan,
            shiftWindow,
            jumpToNow,
            setRangeStart,
            zoom,
            selectGroup,
            followLatestGroup,
            loadActions,
            loadActivityDays,
            refreshTimeline,
            selectActivityDay,
            formatActivityDay,
            refreshIntervalSeconds: REFRESH_INTERVAL_MS / 1000
        };
    },

    template: `
        <div class="container-fluid activity-timeline-page">
            <div class="page-header">
                <div>
                    <h1 class="page-title">
                        <i class="bi bi-activity me-2"></i>
                        {{ t('navigation.activityTimeline') }}
                    </h1>
                    <p class="text-muted mb-0">{{ t('activityTimeline.subtitle') }}</p>
                </div>
                <div class="activity-live-status" :class="{ 'is-live': liveMode }" role="status" aria-live="polite">
                    <span class="activity-live-dot" aria-hidden="true"></span>
                    <span>{{ liveMode ? t('activityTimeline.live') : t('activityTimeline.paused') }}</span>
                    <span v-if="lastUpdatedLabel" class="text-muted">
                        · {{ t('activityTimeline.updatedAt', { time: lastUpdatedLabel }) }}
                    </span>
                </div>
            </div>

            <section class="activity-controls card shadow-sm mb-3" :aria-label="t('activityTimeline.controls')">
                <div class="card-body">
                    <div class="activity-control-group">
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            :aria-label="t('activityTimeline.previousWindow')"
                            :title="t('activityTimeline.previousWindow')"
                            @click="shiftWindow(-1)"
                        >
                            <i class="bi bi-chevron-left" aria-hidden="true"></i>
                        </button>
                        <label class="visually-hidden" for="activity-range-start">{{ t('activityTimeline.rangeStart') }}</label>
                        <input
                            id="activity-range-start"
                            class="form-control activity-range-input"
                            type="datetime-local"
                            :value="rangeStartInput"
                            @change="setRangeStart"
                        />
                        <label class="visually-hidden" for="activity-day-select">{{ t('activityTimeline.activityDays') }}</label>
                        <select
                            id="activity-day-select"
                            class="form-select activity-day-select"
                            :value="selectedActivityDay"
                            :disabled="activityDaysLoading || activityDays.length === 0"
                            @change="selectActivityDay"
                        >
                            <option value="">{{ t('activityTimeline.chooseActivityDay') }}</option>
                            <option v-for="day in activityDays" :key="day.activity_date" :value="day.activity_date">
                                {{ formatActivityDay(day) }}
                            </option>
                        </select>
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            :aria-label="t('activityTimeline.nextWindow')"
                            :title="t('activityTimeline.nextWindow')"
                            @click="shiftWindow(1)"
                        >
                            <i class="bi bi-chevron-right" aria-hidden="true"></i>
                        </button>
                        <button class="btn btn-outline-primary" type="button" @click="jumpToNow">
                            {{ t('activityTimeline.now') }}
                        </button>
                    </div>

                    <div class="activity-control-group">
                        <label class="visually-hidden" for="activity-class-filter">{{ t('activityTimeline.classFilter') }}</label>
                        <select id="activity-class-filter" v-model="classFilter" class="form-select activity-class-filter">
                            <option value="">{{ t('activityTimeline.allClasses') }}</option>
                            <option v-for="classOption in classes" :key="classOption.id" :value="classOption.id">
                                {{ classOption.name }}<template v-if="classOption.teacher"> · {{ classOption.teacher }}</template>
                            </option>
                        </select>
                        <span class="activity-zoom-label">{{ t('activityTimeline.windowLength', { hours: durationHours }) }}</span>
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            :disabled="durationHours === 24"
                            :aria-label="t('activityTimeline.zoomOut')"
                            :title="t('activityTimeline.zoomOut')"
                            @click="zoom(1)"
                        >
                            <i class="bi bi-dash-lg" aria-hidden="true"></i>
                        </button>
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            :disabled="durationHours === 1"
                            :aria-label="t('activityTimeline.zoomIn')"
                            :title="t('activityTimeline.zoomIn')"
                            @click="zoom(-1)"
                        >
                            <i class="bi bi-plus-lg" aria-hidden="true"></i>
                        </button>
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            :disabled="loading"
                            :aria-label="t('activityTimeline.refresh')"
                            :title="t('activityTimeline.refresh')"
                            @click="refreshTimeline"
                        >
                            <i class="bi bi-arrow-clockwise" :class="{ 'activity-spinning': loading }" aria-hidden="true"></i>
                        </button>
                    </div>
                </div>
            </section>

            <div v-if="activityDaysError" class="alert alert-warning d-flex justify-content-between align-items-center" role="alert">
                <span>{{ t('activityTimeline.activityDaysError') }}</span>
                <button class="btn btn-sm btn-outline-warning" type="button" @click="loadActivityDays">
                    {{ t('activityTimeline.retry') }}
                </button>
            </div>

            <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center" role="alert">
                <span><i class="bi bi-exclamation-triangle me-2" aria-hidden="true"></i>{{ t('activityTimeline.loadError') }}</span>
                <button class="btn btn-sm btn-outline-danger" type="button" @click="loadActions">
                    {{ t('activityTimeline.retry') }}
                </button>
            </div>

            <section class="card shadow-sm mb-3 activity-details-card">
                <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
                    <div>
                        <h2 class="h6 mb-1">{{ t('activityTimeline.details') }}</h2>
                        <div v-if="selectedGroup" class="small text-muted">
                            <strong>{{ selectedGroup.className || t('activityTimeline.noClass') }}</strong>
                            <template v-if="selectedGroup.homeroomTeacher"> · {{ selectedGroup.homeroomTeacher }}</template>
                            · {{ formatTime(selectedGroup.startAt) }}–{{ formatTime(selectedGroup.endAt) }}
                            · {{ pluralText('students', selectedGroup.students.length) }}
                        </div>
                    </div>
                    <button
                        v-if="!isLatestSelected"
                        class="btn btn-sm btn-outline-primary"
                        type="button"
                        @click="followLatestGroup"
                    >
                        <i class="bi bi-broadcast me-1" aria-hidden="true"></i>{{ t('activityTimeline.followLatest') }}
                    </button>
                </div>

                <div v-if="!selectedGroup" class="text-muted text-center py-4">
                    {{ t('activityTimeline.noGroupDetails') }}
                </div>
                <template v-else>
                    <div class="activity-summary">
                        <span class="badge activity-count-return">
                            <i class="bi bi-arrow-return-left me-1" aria-hidden="true"></i>
                            {{ pluralText('returnCount', selectedGroup.returnCount) }}
                        </span>
                        <span class="badge activity-count-checkout">
                            <i class="bi bi-book-half me-1" aria-hidden="true"></i>
                            {{ pluralText('checkoutCount', selectedGroup.checkoutCount) }}
                        </span>
                    </div>
                    <div v-if="selectedGroup.students.length === 0" class="text-muted text-center py-4">
                        {{ t('activityTimeline.noStudentActions') }}
                    </div>
                    <div v-else class="activity-student-table-viewport">
                        <table class="table table-sm activity-student-table mb-0">
                            <thead>
                                <tr>
                                    <th scope="col">{{ t('activityTimeline.student') }}</th>
                                    <th scope="col" class="activity-book-column is-return">
                                        <i class="bi bi-arrow-return-left me-1" aria-hidden="true"></i>{{ t('activityTimeline.return') }}
                                    </th>
                                    <th scope="col" class="activity-book-column is-checkout">
                                        <i class="bi bi-book-half me-1" aria-hidden="true"></i>{{ t('activityTimeline.checkout') }}
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="student in selectedGroup.students" :key="student.borrowerId">
                                    <th scope="row" class="activity-student-name">{{ student.borrowerName }}</th>
                                    <td>
                                        <ul v-if="student.returns.length" class="activity-book-list">
                                            <li v-for="item in student.returns" :key="item.id">
                                                {{ item.title }}
                                                <small class="text-muted">{{ item.item_id }} · {{ formatTime(item.occurred_at) }}</small>
                                            </li>
                                        </ul>
                                        <span v-else class="text-muted">0</span>
                                    </td>
                                    <td>
                                        <ul v-if="student.checkouts.length" class="activity-book-list">
                                            <li v-for="item in student.checkouts" :key="item.id">
                                                {{ item.title }}
                                                <small class="text-muted">{{ item.item_id }} · {{ formatTime(item.occurred_at) }}</small>
                                            </li>
                                        </ul>
                                        <span v-else class="text-muted">0</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </template>
            </section>

            <section class="card shadow-sm mb-3 activity-timeline-card" :aria-label="t('activityTimeline.timeline')">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">{{ t('activityTimeline.timeline') }}</h2>
                    <div class="activity-legend">
                        <span><i class="activity-legend-dot is-return" aria-hidden="true"></i>{{ t('activityTimeline.return') }}</span>
                        <span><i class="activity-legend-dot is-checkout" aria-hidden="true"></i>{{ t('activityTimeline.checkout') }}</span>
                    </div>
                </div>
                <div v-if="loading && actions.length === 0" class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">{{ t('activityTimeline.loading') }}</span>
                    </div>
                </div>
                <div v-else-if="timelineEvents.length === 0" class="text-muted text-center py-5">
                    {{ t('activityTimeline.noActions') }}
                </div>
                <div v-else class="activity-timeline-viewport">
                    <svg
                        class="activity-timeline-svg"
                        :viewBox="'0 0 1200 ' + timelineHeight"
                        :height="timelineHeight"
                        role="group"
                        :aria-label="t('activityTimeline.timeline')"
                        @pointerdown="beginPan"
                        @pointermove="movePan"
                        @pointerup="endPan"
                        @pointercancel="endPan"
                    >
                        <g v-for="tick in ticks" :key="tick.x + tick.label" class="activity-timeline-tick">
                            <line :x1="tick.x" :x2="tick.x" :y1="axisY - 8" :y2="axisY + 8"></line>
                            <text :x="tick.x" :y="axisY + 27" text-anchor="middle">{{ tick.label }}</text>
                            <text v-if="tick.dateLabel" :x="tick.x" :y="axisY + 43" text-anchor="middle" class="activity-timeline-date">
                                {{ tick.dateLabel }}
                            </text>
                        </g>

                        <g
                            v-for="entry in timelineGroups"
                            :key="entry.group.id"
                            class="activity-timeline-group"
                            :class="{ 'is-selected': selectedGroup?.id === entry.group.id }"
                            role="button"
                            tabindex="0"
                            @click="selectGroup(entry.group.id)"
                            @keydown.enter.prevent="selectGroup(entry.group.id)"
                            @keydown.space.prevent="selectGroup(entry.group.id)"
                        >
                            <title>{{ entry.label }}</title>
                            <line
                                class="activity-group-bracket"
                                :x1="entry.x1"
                                :x2="entry.x2"
                                :y1="entry.y + 25"
                                :y2="entry.y + 25"
                            ></line>
                            <line
                                class="activity-group-cap"
                                :x1="entry.x1"
                                :x2="entry.x1"
                                :y1="entry.y + 20"
                                :y2="entry.y + 29"
                            ></line>
                            <line
                                class="activity-group-cap"
                                :x1="entry.x2"
                                :x2="entry.x2"
                                :y1="entry.y + 20"
                                :y2="entry.y + 29"
                            ></line>
                            <rect
                                class="activity-group-label-bg"
                                :x="entry.center - entry.width / 2"
                                :y="entry.y"
                                :width="entry.width"
                                height="22"
                                rx="10"
                            ></rect>
                            <text class="activity-group-label" :x="entry.center" :y="entry.y + 15" text-anchor="middle">
                                {{ entry.label }}
                            </text>
                        </g>

                        <line class="activity-timeline-axis" :x1="56" :x2="1172" :y1="axisY" :y2="axisY"></line>
                        <g
                            v-for="event in timelineEvents"
                            :key="event.action.id"
                            class="activity-timeline-event"
                            :class="[
                                event.action.action === 'return' ? 'is-return' : 'is-checkout',
                                { 'is-selected': selectedGroup?.id === event.groupId }
                            ]"
                            role="button"
                            tabindex="0"
                            :aria-label="actionTooltip(event.action, event.actionCount)"
                            @click.stop="selectGroup(event.groupId)"
                            @keydown.enter.prevent="selectGroup(event.groupId)"
                            @keydown.space.prevent="selectGroup(event.groupId)"
                        >
                            <title>{{ actionTooltip(event.action, event.actionCount) }}</title>
                            <line
                                :x1="event.x - 5"
                                :x2="event.x + 5"
                                :y1="axisY"
                                :y2="axisY"
                                :stroke-width="event.strokeWidth + (selectedGroup?.id === event.groupId ? 2 : 0)"
                            ></line>
                        </g>
                    </svg>
                </div>
                <div class="card-footer small text-muted">
                    {{ t('activityTimeline.actionsShown', { count: timelineEvents.length }) }}
                    <span class="ms-2">· {{ t('activityTimeline.dragHint') }}</span>
                </div>
            </section>

        </div>
    `
});
