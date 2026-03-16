import { Component } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { MorphologyResponse, NERService } from './ner.service';

export interface Highligtables {
  text: string;
  person: Match[];
  known_persons: Match[];
  location: Match[];
  organisation: Match[];
  phone_numbers: Match[];
  email_addresses: Match[];
  id_numbers: Match[];
  dates: Match[];
  addresses: Match[];
  count: number;
}

interface Match {
  match: string;
  slots: number[][];
}

type EntityType =
  | 'person'
  | 'known_persons'
  | 'location'
  | 'organisation'
  | 'phone_numbers'
  | 'email_addresses'
  | 'id_numbers'
  | 'dates'
  | 'addresses';

interface EntityStyle {
  label: string;
  color: string;
  selected: string;
}

interface ProcessedPart {
  text: string;
  normal: boolean;
  match?: string;
  type?: EntityType;
  key?: string;
  color?: string;
  selected?: string;
}

interface SelectableEntity {
  key: string;
  match: string;
  type: EntityType;
  color: string;
  selected: string;
  custom?: string;
}

interface EntityGroup {
  type: EntityType;
  label: string;
  items: SelectableEntity[];
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  currentPage: 'anonymiser' | 'morphology' = 'anonymiser';

  fileToUpload: File | null = null;
  userInput = '';
  hasStartedAnonymiser = false;
  isEditingCurrentText = false;
  editorText = '';
  anonymizerLoading = false;

  wordsToHighlight: Highligtables = {
    text: '',
    person: [],
    known_persons: [],
    location: [],
    organisation: [],
    phone_numbers: [],
    email_addresses: [],
    id_numbers: [],
    dates: [],
    addresses: [],
    count: 0
  };

  isCustomizable = false;
  processedText: ProcessedPart[] = [];
  selectableEntities: SelectableEntity[] = [];
  entityGroups: EntityGroup[] = [];
  selectedMatches: SelectableEntity[] = [];
  anonymizeOption = 'words';

  morphologyInput = '';
  morphologyResult: MorphologyResponse | null = null;
  morphologyLoading = false;
  morphologyTargetCase = '';
  morphologyCombineWords = false;

  private readonly alreadyAnonymizedKeys = new Set<string>();
  private readonly blockedReplacementMatches = new Set<string>();

  private readonly entityStyles: Record<EntityType, EntityStyle> = {
    person: { label: 'Inimene', color: '#ffc86f', selected: '#ffab3d' },
    known_persons: { label: 'Tuntud isik (Wiki)', color: '#e5e7eb', selected: '#d1d5db' },
    organisation: { label: 'Organisatsioon', color: '#ff8a8a', selected: '#ff6262' },
    location: { label: 'Asukoht', color: '#8ecbff', selected: '#5db4ff' },
    phone_numbers: { label: 'Telefon', color: '#f9b168', selected: '#f48b2d' },
    email_addresses: { label: 'E-post', color: '#b39dff', selected: '#9176ff' },
    id_numbers: { label: 'Isikukood', color: '#87d897', selected: '#58c46f' },
    dates: { label: 'Kuupäev', color: '#99d0ff', selected: '#6db9ff' },
    addresses: { label: 'Aadress', color: '#ff9bbb', selected: '#ff6f9e' }
  };

  private readonly entityTypes: EntityType[] = [
    'person',
    'organisation',
    'location',
    'phone_numbers',
    'email_addresses',
    'id_numbers',
    'dates',
    'addresses',
    'known_persons'
  ];

  private readonly caseLabels: Record<string, string> = {
    Nom: 'Nimetav',
    Gen: 'Omastav',
    Par: 'Osastav',
    Ill: 'Sisseütlev',
    Ine: 'Seesütlev',
    Ela: 'Seestütlev',
    All: 'Alaleütlev',
    Ade: 'Alalütlev',
    Abl: 'Alaltütlev',
    Tra: 'Saav',
    Ter: 'Rajav',
    Ess: 'Olev',
    Abe: 'Ilmaütlev',
    Com: 'Kaasaütlev'
  };

  constructor(private nerService: NERService) {}

  switchPage(page: 'anonymiser' | 'morphology'): void {
    this.currentPage = page;
  }

  onFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.fileToUpload = target.files?.[0] || null;
  }

  onUpload(): void {
    if (!this.userInput.trim() && !this.fileToUpload) {
      return;
    }

    this.anonymizerLoading = true;
    this.selectedMatches = [];
    this.isEditingCurrentText = false;

    if (this.userInput.trim()) {
      this.nerService.getNamedEntities(this.userInput).subscribe(
        (response: Highligtables) => {
          this.hasStartedAnonymiser = true;
          this.applyDetection(response);
          this.anonymizerLoading = false;
        },
        (error: HttpErrorResponse) => {
          console.error('Upload error', error);
          this.anonymizerLoading = false;
        }
      );
      return;
    }

    if (this.fileToUpload) {
      this.nerService.getNamedEntitiesFile(this.fileToUpload).subscribe(
        (response: Highligtables) => {
          this.hasStartedAnonymiser = true;
          this.userInput = response.text;
          this.applyDetection(response);
          this.anonymizerLoading = false;
        },
        (error: HttpErrorResponse) => {
          console.error('Upload error', error);
          this.anonymizerLoading = false;
        }
      );
    }
  }

  submitSelections(): void {
    if (!this.selectedMatches.length) {
      return;
    }

    const selectedMatchesData = this.selectedMatches.map((selected) => {
      const matchedEntity = this.wordsToHighlight[selected.type].find(
        (item) => item.match === selected.match
      );

      return {
        match: selected.match,
        slots: matchedEntity ? matchedEntity.slots : [],
        custom: selected.custom || null,
        type: selected.type
      };
    });

    const anonymizedNow = this.selectedMatches.map((item) => item.key);

    this.anonymizerLoading = true;
    this.nerService
      .submitSelectedMatches(selectedMatchesData, this.wordsToHighlight.text, this.anonymizeOption)
      .subscribe(
        (response) => {
          const parsed = this.parseAnonymizeResponse(response);
          anonymizedNow.forEach((key) => this.alreadyAnonymizedKeys.add(key));
          this.addBlockedReplacementTerms(parsed.blockedTerms);
          this.selectedMatches = [];
          this.userInput = parsed.text;
          this.reanalyzeCurrentText(parsed.text);
        },
        (error: HttpErrorResponse) => {
          console.error('Error submitting selections', error);
          this.anonymizerLoading = false;
        }
      );
  }

  selectMatchByKey(key: string): void {
    const existing = this.selectedMatches.find((m) => m.key === key);

    if (existing) {
      this.selectedMatches = this.selectedMatches.filter((m) => m.key !== key);
      return;
    }

    const entity = this.selectableEntities.find((item) => item.key === key);
    if (entity) {
      this.selectedMatches.push({ ...entity });
    }
  }

  toggleAllSelections(): void {
    if (this.selectedMatches.length === this.selectableEntities.length) {
      this.selectedMatches = [];
      return;
    }

    const customMap = new Map(this.selectedMatches.map((item) => [item.key, item.custom]));
    this.selectedMatches = this.selectableEntities.map((entity) => ({
      ...entity,
      custom: customMap.get(entity.key)
    }));
  }

  clearSelections(): void {
    this.selectedMatches = [];
  }

  removeMatch(key: string): void {
    this.selectedMatches = this.selectedMatches.filter((m) => m.key !== key);
  }

  getSelectedCount(type: EntityType): number {
    return this.selectedMatches.filter((item) => item.type === type).length;
  }

  isSelected(key: string): boolean {
    return this.selectedMatches.some((m) => m.key === key);
  }

  openEditMode(): void {
    this.editorText = this.wordsToHighlight.text;
    this.isEditingCurrentText = true;
  }

  cancelEditMode(): void {
    this.isEditingCurrentText = false;
    this.editorText = '';
  }

  applyEditedText(): void {
    if (!this.editorText.trim()) {
      return;
    }

    this.userInput = this.editorText;
    this.selectedMatches = [];
    this.isEditingCurrentText = false;
    this.anonymizerLoading = true;
    this.reanalyzeCurrentText(this.editorText);
  }

  resetAnonymiser(): void {
    this.hasStartedAnonymiser = false;
    this.isEditingCurrentText = false;
    this.anonymizerLoading = false;
    this.fileToUpload = null;
    this.userInput = '';
    this.editorText = '';
    this.selectedMatches = [];
    this.selectableEntities = [];
    this.entityGroups = [];
    this.processedText = [];
    this.wordsToHighlight = {
      text: '',
      person: [],
      known_persons: [],
      location: [],
      organisation: [],
      phone_numbers: [],
      email_addresses: [],
      id_numbers: [],
      dates: [],
      addresses: [],
      count: 0
    };
    this.alreadyAnonymizedKeys.clear();
    this.blockedReplacementMatches.clear();
  }

  runMorphology(): void {
    if (!this.morphologyInput.trim()) {
      return;
    }

    this.morphologyLoading = true;
    this.morphologyResult = null;
    this.nerService.getMorphology(this.morphologyInput, this.morphologyTargetCase, this.morphologyCombineWords).subscribe(
      (response) => {
        this.morphologyResult = response;
        this.morphologyLoading = false;
      },
      (error: HttpErrorResponse) => {
        console.error('Morphology request error', error);
        this.morphologyLoading = false;
      }
    );
  }

  resetMorphology(): void {
    this.morphologyInput = '';
    this.morphologyResult = null;
    this.morphologyLoading = false;
    this.morphologyTargetCase = '';
    this.morphologyCombineWords = false;
  }

  formatCaseLabel(caseCode: string): string {
    if (!caseCode) {
      return '-';
    }
    const estonian = this.caseLabels[caseCode];
    return estonian ? `${caseCode} (${estonian})` : caseCode;
  }

  get morphologyCaseOptions(): string[] {
    return Object.keys(this.caseLabels);
  }

  private reanalyzeCurrentText(text: string): void {
    this.nerService.getNamedEntities(text).subscribe(
      (response: Highligtables) => {
        this.applyDetection(response);
        this.anonymizerLoading = false;
      },
      (error: HttpErrorResponse) => {
        console.error('Reanalysis error', error);
        this.anonymizerLoading = false;
      }
    );
  }

  private applyDetection(data: Highligtables): void {
    const filtered = this.filterAlreadyAnonymized(data);
    this.wordsToHighlight = filtered;
    this.processText(filtered);
  }

  private filterAlreadyAnonymized(data: Highligtables): Highligtables {
    const filtered: Highligtables = {
      ...data,
      person: [],
      known_persons: [],
      location: [],
      organisation: [],
      phone_numbers: [],
      email_addresses: [],
      id_numbers: [],
      dates: [],
      addresses: [],
      count: 0
    };

    this.entityTypes.forEach((type) => {
      const items = data[type].filter((matchObj) => {
        if (this.alreadyAnonymizedKeys.has(this.entityKey(type, matchObj.match))) {
          return false;
        }
        if (this.isBlockedReplacementMatch(matchObj.match)) {
          return false;
        }
        return true;
      });
      filtered[type] = items;
    });

    filtered.count = this.entityTypes.reduce((sum, type) => sum + filtered[type].length, 0);
    return filtered;
  }

  private processText(data: Highligtables): void {
    const slots: Array<{
      start: number;
      end: number;
      match: string;
      type: EntityType;
      color: string;
      selected: string;
      key: string;
    }> = [];

    const uniqueEntities = new Map<string, SelectableEntity>();

    this.entityTypes.forEach((type) => {
      const style = this.entityStyles[type];
      const entityData = data[type];

      entityData.forEach((matchObj) => {
        const key = this.entityKey(type, matchObj.match);

        if (!uniqueEntities.has(key)) {
          uniqueEntities.set(key, {
            key,
            match: matchObj.match,
            type,
            color: style.color,
            selected: style.selected
          });
        }

        matchObj.slots.forEach((slot) => {
          slots.push({
            start: slot[0],
            end: slot[1],
            match: matchObj.match,
            type,
            color: style.color,
            selected: style.selected,
            key
          });
        });
      });
    });

    slots.sort((a, b) => a.start - b.start);

    this.processedText = [];
    let lastIndex = 0;

    slots.forEach((slot) => {
      if (lastIndex < slot.start) {
        this.processedText.push({
          text: data.text.substring(lastIndex, slot.start),
          normal: true
        });
      }

      this.processedText.push({
        text: data.text.substring(slot.start, slot.end),
        normal: false,
        match: slot.match,
        type: slot.type,
        key: slot.key,
        color: slot.color,
        selected: slot.selected
      });

      lastIndex = slot.end;
    });

    if (lastIndex < data.text.length) {
      this.processedText.push({
        text: data.text.substring(lastIndex),
        normal: true
      });
    }

    this.selectableEntities = Array.from(uniqueEntities.values()).sort((a, b) =>
      a.match.localeCompare(b.match)
    );

    this.entityGroups = this.entityTypes
      .map((type) => ({
        type,
        label: this.entityStyles[type].label,
        items: this.selectableEntities.filter((entity) => entity.type === type)
      }))
      .filter((group) => group.items.length > 0);
  }

  private entityKey(type: EntityType, match: string): string {
    return `${type}::${match}`;
  }

  private parseAnonymizeResponse(response: any): { text: string; blockedTerms: string[] } {
    if (typeof response === 'string') {
      return { text: response, blockedTerms: [] };
    }
    if (response && typeof response === 'object') {
      return {
        text: typeof response.text === 'string' ? response.text : '',
        blockedTerms: Array.isArray(response.blocked_terms) ? response.blocked_terms : []
      };
    }
    return { text: '', blockedTerms: [] };
  }

  private addBlockedReplacementTerms(terms: string[]): void {
    terms.forEach((term) => {
      const normalized = this.normalizeTerm(term);
      if (!normalized) {
        return;
      }
      this.blockedReplacementMatches.add(normalized);
      normalized.split(' ').forEach((part) => {
        const trimmed = part.trim();
        if (trimmed.length >= 2) {
          this.blockedReplacementMatches.add(trimmed);
        }
      });
    });
  }

  private isBlockedReplacementMatch(match: string): boolean {
    const normalized = this.normalizeTerm(match);
    return this.blockedReplacementMatches.has(normalized);
  }

  private normalizeTerm(term: string): string {
    return term.replace(/\s+/g, ' ').trim().toLowerCase();
  }
}
