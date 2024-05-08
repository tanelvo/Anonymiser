import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Highligtables } from './app.component';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class NERService {

  constructor(protected httpClient: HttpClient) { }

  getNamedEntities(text: string): Observable<Highligtables> {
    const body = text;
    return this.httpClient.post<Highligtables>('http://localhost:8080/text/', body);
  }

  getNamedEntitiesFile(file: File): Observable<{highlightables: Highligtables, text: string}> {
    const formData: FormData = new FormData();
    formData.append('file', file, file.name);
    return this.httpClient.post<{highlightables: Highligtables, text: string}>('http://localhost:8080/file/', formData)
  }
}
