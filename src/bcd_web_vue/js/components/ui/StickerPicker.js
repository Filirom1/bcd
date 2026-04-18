/**
 * StickerPicker Component
 * Palette of colored emoji shapes for shelf location labels.
 * Clicking a sticker prepends it to the current value (or replaces a leading emoji).
 */

const { defineComponent } = Vue;

// Emoji regex to detect a leading emoji in a string
const LEADING_EMOJI_RE = /^(\p{Emoji_Presentation}|\p{Extended_Pictographic})\s*/u;

// Row 1: circles  Row 2: squares — same color order left to right
const STICKERS_ROW1 = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪'];
const STICKERS_ROW2 = ['🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '🟫', '⬛', '⬜'];

/**
 * Apply a sticker to a location string.
 * - If value starts with an emoji → replace it with the new one.
 * - Otherwise → prepend emoji + space.
 */
export function applySticker(value, emoji) {
    const stripped = (value || '').replace(LEADING_EMOJI_RE, '').trimStart();
    return emoji + ' ' + stripped;
}

export default defineComponent({
    name: 'StickerPicker',

    props: {
        modelValue: {
            type: String,
            default: ''
        }
    },

    emits: ['update:modelValue'],

    setup(props, { emit }) {
        const pick = (emoji) => {
            emit('update:modelValue', applySticker(props.modelValue, emoji));
        };

        return { pick, STICKERS_ROW1, STICKERS_ROW2 };
    },

    template: `
        <div class="sticker-picker mt-1" style="width:fit-content;">
            <div class="d-flex gap-1">
                <button
                    v-for="s in STICKERS_ROW1"
                    :key="s"
                    type="button"
                    class="btn p-0 border-0 lh-1"
                    style="font-size:1.5rem; background:none; cursor:pointer; width:2rem; text-align:center;"
                    :title="s"
                    @click.prevent="pick(s)"
                >{{ s }}</button>
            </div>
            <div class="d-flex gap-1 mt-1">
                <button
                    v-for="s in STICKERS_ROW2"
                    :key="s"
                    type="button"
                    class="btn p-0 border-0 lh-1"
                    style="font-size:1.5rem; background:none; cursor:pointer; width:2rem; text-align:center;"
                    :title="s"
                    @click.prevent="pick(s)"
                >{{ s }}</button>
            </div>
        </div>
    `
});
