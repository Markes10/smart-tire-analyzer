// Minimal type declarations for 'zustand' to satisfy TypeScript in environments
// where the package types are not installed. These are intentionally loose.
declare module "zustand" {
    export type SetState<T> = (
        partial: Partial<T> | ((state: T) => Partial<T>),
        replace?: boolean
    ) => void;
    export type GetState<T> = () => T;
    export type StateCreator<T> = (set: SetState<T>, get: GetState<T>, api?: any) => T;

    // create can be called as `create(fn)` or `create()<fn>` when using middleware helper pattern
    export function create<T>(fn: StateCreator<T>): any;
    export function create<T>(): (fn: StateCreator<T>) => any;
    export default create;
}

declare module "zustand/middleware" {
    import { StateCreator } from "zustand";

    // persist wraps a StateCreator and returns a StateCreator
    export function persist<T>(stateCreator: StateCreator<T>, options?: any): StateCreator<T>;

    // createJSONStorage returns a storage adapter used by persist
    export function createJSONStorage(storageFactory: () => any): any;

    export default persist;
}
