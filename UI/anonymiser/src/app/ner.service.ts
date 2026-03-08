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
    const body = {text};
    return this.httpClient.post<Highligtables>('http://192.168.1.235:8080/text/', body);
  }

  getNamedEntitiesFile(file: File): Observable<Highligtables> {
    const formData: FormData = new FormData();
    formData.append('file', file, file.name);
    return this.httpClient.post<Highligtables>('http://192.168.1.235:8080/file/', formData)
  }

  submitSelectedMatches(selectedMatches: any[], text: string, anonymize: string): Observable<any> {
    return this.httpClient.post<string>('http://192.168.1.235:8080/anonymise/', { text: text, matches: selectedMatches, anonymize });
  }
}
