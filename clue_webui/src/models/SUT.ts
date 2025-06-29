export interface Variant {
  name: string;
  description?: string;
}

export interface SUT {
  name: string;
  variants: Variant[];
}
