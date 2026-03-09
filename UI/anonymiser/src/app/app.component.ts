import { Component } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { NERService } from './ner.service';

export interface Highligtables {
  text: string;
  person: Match[];
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
  fileToUpload: File | null = null;
  userInput = '';

  wordsToHighlight: Highligtables = {
    text: '',
    person: [],
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
  anomyizedText = '';
  anonymizeOption = 'words';

  private readonly entityStyles: Record<EntityType, EntityStyle> = {
    person: { label: 'Inimene', color: '#ffc86f', selected: '#ffab3d' },
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
    'addresses'
  ];

  constructor(private nerService: NERService) {}

  onFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.fileToUpload = target.files?.[0] || null;
  }

  onUpload(): void {
    this.processedText = [];
    this.selectableEntities = [];
    this.entityGroups = [];
    this.selectedMatches = [];
    this.anomyizedText = '';

    if (this.userInput.trim()) {
      this.nerService.getNamedEntities(this.userInput).subscribe(
        (response: Highligtables) => {
          this.wordsToHighlight = response;
          this.processText(response);
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
      return;
    }

    if (this.fileToUpload) {
      this.nerService.getNamedEntitiesFile(this.fileToUpload).subscribe(
        (response: Highligtables) => {
          this.wordsToHighlight = response;
          this.processText(response);
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }
  }

  processText(data: Highligtables): void {
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

    this.nerService
      .submitSelectedMatches(selectedMatchesData, this.wordsToHighlight.text, this.anonymizeOption)
      .subscribe(
        (response) => {
          this.anomyizedText = response;
        },
        (error: HttpErrorResponse) => {
          console.error('Error submitting selections', error);
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

  get formattedVariable(): string {
    return this.anomyizedText.replace(/\n/g, '<br>');
  }

  getSelectedCount(type: EntityType): number {
    return this.selectedMatches.filter((item) => item.type === type).length;
  }

  isSelected(key: string): boolean {
    return this.selectedMatches.some((m) => m.key === key);
  }

  private entityKey(type: EntityType, match: string): string {
    return `${type}::${match}`;
  }
}
