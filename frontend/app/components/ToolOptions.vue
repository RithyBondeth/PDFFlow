<script setup lang="ts">
import type { Operation } from '~/types/api'
import type { OrganizedPage } from '~/utils/pageOrganizer'
import { createPagePlan } from '~/utils/pageOrganizer'

/**
 * Per-tool option form. Kept explicit rather than generated from the JSON
 * schema: each tool has a handful of options and a hand-written control reads
 * far better than a generic schema renderer.
 */
const props = defineProps<{
  operation: Operation
  pageCount?: number | null
  /** The browser's copy of the upload, for local page previews. */
  file?: File | null
}>()
const options = defineModel<Record<string, unknown>>({ required: true })
/** Whether the current options can be submitted. */
const valid = defineModel<boolean>('valid', { default: true })

function set(key: string, value: unknown) {
  options.value = { ...options.value, [key]: value }
}

// Sensible defaults so the run button works without touching anything.
watch(
  () => [props.operation.key, props.pageCount] as const,
  ([key, pageCount]) => {
    if (key === 'compress') options.value = { level: 'medium' }
    else if (key === 'rotate') options.value = { angle: 90, pages: '' }
    else if (key === 'split') options.value = { mode: 'every_page', ranges: '' }
    else if (key === 'organize') options.value = { pages: createPagePlan(pageCount ?? 0) }
    else if (key === 'images_to_pdf') options.value = { pageSize: 'fit', margin: 'none' }
    else if (key === 'pdf_to_images') options.value = { format: 'png', dpi: 150, pages: '' }
    else if (key === 'protect') options.value = { password: '', allowPrinting: true, allowCopying: true }
    else if (key === 'unlock') options.value = { password: '' }
    else options.value = {}
  },
  { immediate: true },
)

// The confirmation lives only here. It is never part of `options`, so it is
// never sent anywhere.
const confirmPassword = ref('')
const showPassword = ref(false)
const password = computed(() => (options.value.password as string | undefined) ?? '')

// Cleared together with the password (after a run, or on switching tool).
watch(password, (value) => {
  if (!value) confirmPassword.value = ''
})

const passwordMismatch = computed(
  () =>
    props.operation.key === 'protect' &&
    confirmPassword.value.length > 0 &&
    confirmPassword.value !== password.value,
)

watchEffect(() => {
  const key = props.operation.key
  if (key === 'protect') valid.value = password.value.length > 0 && confirmPassword.value === password.value
  else if (key === 'unlock') valid.value = password.value.length > 0
  else valid.value = true
})

const PAGE_SIZES = [
  { value: 'fit', label: 'Fit image', hint: 'Each page matches its image' },
  { value: 'a4', label: 'A4', hint: '210 × 297 mm' },
  { value: 'letter', label: 'Letter', hint: '8.5 × 11 in' },
]

const MARGINS = [
  { value: 'none', label: 'None' },
  { value: 'small', label: 'Small' },
  { value: 'large', label: 'Large' },
]

const IMAGE_FORMATS = [
  { value: 'png', label: 'PNG', hint: 'Sharp text, larger files' },
  { value: 'jpeg', label: 'JPEG', hint: 'Small files, best for photos' },
  { value: 'webp', label: 'WEBP', hint: 'Smallest, for the web' },
]

const RESOLUTIONS = [
  { value: 72, label: '72 DPI', hint: 'Screen preview' },
  { value: 150, label: '150 DPI', hint: 'Recommended' },
  { value: 300, label: '300 DPI', hint: 'Print quality' },
]

const COMPRESSION_LEVELS = [
  { value: 'low', label: 'Low', hint: 'Best quality, smallest saving' },
  { value: 'medium', label: 'Medium', hint: 'Recommended balance' },
  { value: 'high', label: 'High', hint: 'Smallest file, softer images' },
]
</script>

<template>
  <div class="panel space-y-5 p-5 sm:p-6">
    <h2 class="font-data text-xs uppercase tracking-[0.2em] text-ink-faint">
      Options
    </h2>

    <!-- Compress -->
    <div v-if="operation.key === 'compress'" class="grid gap-2 sm:grid-cols-3">
      <button
        v-for="level in COMPRESSION_LEVELS"
        :key="level.value"
        type="button"
        class="rounded-md border p-3 text-left transition-colors duration-200"
        :class="options.level === level.value
          ? 'border-accent-500 bg-accent-500/10'
          : 'border-hairline hover:border-hairline-strong'"
        @click="set('level', level.value)"
      >
        <span class="block font-medium text-ink">{{ level.label }}</span>
        <span class="mt-0.5 block text-xs leading-snug text-ink-muted">{{ level.hint }}</span>
      </button>
    </div>

    <!-- Rotate -->
    <template v-else-if="operation.key === 'rotate'">
      <UFormField label="Angle">
        <div class="flex gap-2">
          <UButton
            v-for="angle in [90, 180, 270]"
            :key="angle"
            :color="options.angle === angle ? 'primary' : 'neutral'"
            :variant="options.angle === angle ? 'solid' : 'outline'"
            @click="set('angle', angle)"
          >
            {{ angle }}°
          </UButton>
        </div>
      </UFormField>
      <UFormField label="Pages" hint="Leave blank to rotate every page">
        <UInput
          :model-value="(options.pages as string) ?? ''"
          placeholder="e.g. 1-3,7"
          @update:model-value="set('pages', $event)"
        />
      </UFormField>
    </template>

    <!-- Split -->
    <template v-else-if="operation.key === 'split'">
      <UFormField label="How to split">
        <URadioGroup
          :model-value="options.mode as string"
          :items="[
            { value: 'every_page', label: 'One PDF per page' },
            { value: 'ranges', label: 'By page range' },
          ]"
          @update:model-value="set('mode', $event)"
        />
      </UFormField>
      <UFormField
        v-if="options.mode === 'ranges'"
        label="Ranges"
        hint="Each range becomes its own PDF"
      >
        <UInput
          :model-value="(options.ranges as string) ?? ''"
          placeholder="e.g. 1-3,4-6,7"
          @update:model-value="set('ranges', $event)"
        />
      </UFormField>
    </template>

    <!-- Extract pages -->
    <UFormField
      v-else-if="operation.key === 'extract_pages'"
      label="Pages to keep"
      hint="Blank keeps every page"
    >
      <UInput
        :model-value="(options.pages as string) ?? ''"
        placeholder="e.g. 2,5-9"
        @update:model-value="set('pages', $event)"
      />
    </UFormField>

    <!-- Images to PDF -->
    <template v-else-if="operation.key === 'images_to_pdf'">
      <UFormField label="Page size">
        <div class="grid gap-2 sm:grid-cols-3">
          <button
            v-for="size in PAGE_SIZES"
            :key="size.value"
            type="button"
            class="rounded-md border p-3 text-left transition-colors duration-200"
            :class="options.pageSize === size.value
              ? 'border-accent-500 bg-accent-500/10'
              : 'border-hairline hover:border-hairline-strong'"
            @click="set('pageSize', size.value)"
          >
            <span class="block font-medium text-ink">{{ size.label }}</span>
            <span class="mt-0.5 block text-xs leading-snug text-ink-muted">{{ size.hint }}</span>
          </button>
        </div>
      </UFormField>
      <UFormField label="Margin">
        <div class="flex gap-2">
          <UButton
            v-for="margin in MARGINS"
            :key="margin.value"
            :color="options.margin === margin.value ? 'primary' : 'neutral'"
            :variant="options.margin === margin.value ? 'solid' : 'outline'"
            @click="set('margin', margin.value)"
          >
            {{ margin.label }}
          </UButton>
        </div>
      </UFormField>
    </template>

    <!-- PDF to images -->
    <template v-else-if="operation.key === 'pdf_to_images'">
      <UFormField label="Image format">
        <div class="grid gap-2 sm:grid-cols-3">
          <button
            v-for="format in IMAGE_FORMATS"
            :key="format.value"
            type="button"
            class="rounded-md border p-3 text-left transition-colors duration-200"
            :class="options.format === format.value
              ? 'border-accent-500 bg-accent-500/10'
              : 'border-hairline hover:border-hairline-strong'"
            @click="set('format', format.value)"
          >
            <span class="block font-medium text-ink">{{ format.label }}</span>
            <span class="mt-0.5 block text-xs leading-snug text-ink-muted">{{ format.hint }}</span>
          </button>
        </div>
      </UFormField>
      <UFormField label="Resolution">
        <div class="grid gap-2 sm:grid-cols-3">
          <button
            v-for="resolution in RESOLUTIONS"
            :key="resolution.value"
            type="button"
            class="rounded-md border p-3 text-left transition-colors duration-200"
            :class="options.dpi === resolution.value
              ? 'border-accent-500 bg-accent-500/10'
              : 'border-hairline hover:border-hairline-strong'"
            @click="set('dpi', resolution.value)"
          >
            <span class="block font-medium text-ink">{{ resolution.label }}</span>
            <span class="mt-0.5 block text-xs leading-snug text-ink-muted">{{ resolution.hint }}</span>
          </button>
        </div>
      </UFormField>
      <UFormField label="Pages" hint="Leave blank to convert every page">
        <UInput
          :model-value="(options.pages as string) ?? ''"
          placeholder="e.g. 1-3,7"
          @update:model-value="set('pages', $event)"
        />
      </UFormField>
    </template>

    <!-- Protect -->
    <template v-else-if="operation.key === 'protect'">
      <div class="grid gap-4 sm:grid-cols-2">
        <UFormField label="Password" hint="Needed to open the PDF">
          <UInput
            :model-value="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="off"
            class="w-full"
            @update:model-value="set('password', $event)"
          >
            <template #trailing>
              <UButton
                color="neutral"
                variant="link"
                size="xs"
                :icon="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
                @click="showPassword = !showPassword"
              />
            </template>
          </UInput>
        </UFormField>
        <UFormField
          label="Confirm password"
          :error="passwordMismatch ? 'The passwords do not match' : undefined"
        >
          <UInput
            v-model="confirmPassword"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="off"
            class="w-full"
          />
        </UFormField>
      </div>

      <UFormField
        label="Permissions"
        hint="Most PDF readers honour these, but they are not a guarantee"
      >
        <div class="flex flex-col gap-2 sm:flex-row sm:gap-6">
          <UCheckbox
            :model-value="options.allowPrinting as boolean"
            label="Allow printing"
            @update:model-value="set('allowPrinting', $event === true)"
          />
          <UCheckbox
            :model-value="options.allowCopying as boolean"
            label="Allow copying text and images"
            @update:model-value="set('allowCopying', $event === true)"
          />
        </div>
      </UFormField>

      <p class="flex items-start gap-2 text-xs leading-relaxed text-ink-muted">
        <UIcon name="i-lucide-key-round" class="mt-0.5 size-3.5 shrink-0 text-accent-ink" />
        Encrypted with AES-256. PDFFlow never stores your password and cannot
        recover it, so keep it somewhere safe.
      </p>
    </template>

    <!-- Unlock -->
    <template v-else-if="operation.key === 'unlock'">
      <UFormField
        label="Password"
        hint="The password that opens the PDF, or its owner password"
      >
        <UInput
          :model-value="password"
          :type="showPassword ? 'text' : 'password'"
          autocomplete="off"
          class="w-full sm:max-w-sm"
          @update:model-value="set('password', $event)"
        >
          <template #trailing>
            <UButton
              color="neutral"
              variant="link"
              size="xs"
              :icon="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              @click="showPassword = !showPassword"
            />
          </template>
        </UInput>
      </UFormField>
      <p class="flex items-start gap-2 text-xs leading-relaxed text-ink-muted">
        <UIcon name="i-lucide-shield-check" class="mt-0.5 size-3.5 shrink-0 text-accent-ink" />
        Used once to decrypt your file, then discarded. It is never stored.
      </p>
    </template>

    <!-- Organize pages -->
    <PageOrganizer
      v-else-if="operation.key === 'organize'"
      :model-value="(options.pages as OrganizedPage[]) ?? []"
      :file="file"
      @update:model-value="set('pages', $event)"
    />

    <p v-else class="text-sm text-ink-muted">
      This tool has no options — just run it.
    </p>
  </div>
</template>
