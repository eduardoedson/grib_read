# -*- coding: utf-8 -*-
'''
requires 

1) ecCodes version 2.8 or above (available at https://confluence.ecmwf.int/display/ECC/Releases)
2) python2.7

To run the program

   python read.py -g grib_file.bufr -p 1 -o data.json
'''
import argparse 
import json
import time


from eccodes import *


def calcTamGrade(lats, longs):
    """
    Tamanho da grade

    x = ultima longitude - primeira longitude 
    y = ultima latitude - primeira latitude

    """
    return [((longs[1]) - (longs[0])), ((lats[1]) - (lats[0]))]


def calcDistPontos(grade, ni, nj):
    """
    Distância entre os pontos da grade
    dy = grade[0] / nj
    dx = grade[1] / ni
    """
    return [(float(grade[0]) / float(nj)), (float(grade[1]) / float(ni))]


def verificaPonto(coord, limites, distP):
    if ((coord >= limites[0]) and (coord <= limites[1])):
        return int(round(((coord) - (limites[0])) / distP))
    else:
        exit(1)


def calcIndices(lats, longs, lat, lon, distP):
    """
    Calcula o índice equivalente ao ponto mais próximo da grade
    """
    return [
        [  
            1 if verificaPonto(lon, longs, distP[0]) <= 0 else verificaPonto(lon, longs, distP[0]),
            1 if verificaPonto(lon, longs, distP[0]) <= 0 else verificaPonto(lon, longs, distP[0]) - 1
        ],
        [
            1 if verificaPonto(lat, lats, distP[1]) <= 0 else verificaPonto(lat, lats, distP[1]),
            1 if verificaPonto(lat, lats, distP[1]) <= 0 else verificaPonto(lat, lats, distP[1]) - 1
        ]
    ]


def calcPontosProx(indices, distP, lats, longs):
    """
    Calcula os pontos próximos
    """
    return [
        [longs[0] + indices[0][0] * distP[1], longs[0] + indices[0][1] * distP[1]],
        [lats[0] + indices[1][0] * distP[0], lats[0] + indices[1][1] * distP[0]]
    ]


def calcDistancia(lat, lon, pontos, indices):
    """
    Calcula distância dos pontos próximos
    """
    return [
        {'Distancia': (((lon - pontos[0][0])**2) + ((lat - pontos[1][0])**2)), 'Lat': pontos[1][0], 'Lon': pontos[0][0], 'Pos': indices[1][0] * indices[0][0]},
        {'Distancia': (((lon - pontos[0][0])**2) + ((lat - pontos[1][1])**2)), 'Lat': pontos[1][1], 'Lon': pontos[0][0], 'Pos': indices[1][1] * indices[0][0]},
        {'Distancia': (((lon - pontos[0][1])**2) + ((lat - pontos[1][0])**2)), 'Lat': pontos[1][0], 'Lon': pontos[0][1], 'Pos': indices[1][0] * indices[0][1]},
        {'Distancia': (((lon - pontos[0][1])**2) + ((lat - pontos[1][1])**2)), 'Lat': pontos[1][1], 'Lon': pontos[0][1], 'Pos': indices[1][1] * indices[0][1]}
    ]


def acharMenorDistancia(distancias):
    menor = distancias[0]
    for d in distancias:
        if d['Distancia'] < menor['Distancia']:
            menor = d
    return menor


def pegarValor(indice, param, pk):
    indice -= 1
    i = 1
    f = open(param, 'rb')
    while 1:
        gid = codes_grib_new_from_file(f)
        if gid is None:
            break
        if int(pk) == i:
            values = codes_get_values(gid)
            break
        else:
            i += 1
    codes_release(gid)
    f.close()
    return values[indice]


def pegarValores(arquivo, grib_position = 1):
    """
    Pega todos os valores do grib e suas coordenadas
    """
    f = open(arquivo)
    i = 1
    while 1:
        gid = codes_grib_new_from_file(f)
        if gid is None:
            break

        if int(grib_position) == i:
            f_lat = codes_get(gid, 'latitudeOfFirstGridPointInDegrees')
            l_lat = codes_get(gid, 'latitudeOfLastGridPointInDegrees')
            f_lon = codes_get(gid, 'longitudeOfFirstGridPointInDegrees')
            l_lon = codes_get(gid, 'longitudeOfLastGridPointInDegrees')
            ni = codes_get(gid, 'Ni')
            nj = codes_get(gid, 'Nj')
            i_increment = codes_get(gid, 'iDirectionIncrementInDegrees')
            j_increment = codes_get(gid, 'jDirectionIncrementInDegrees')
            total_valores = codes_get(gid, 'numberOfValues')
            break
        else:
            i += 1

        codes_release(gid)
    f.close()

    data = []

    tamGrade = calcTamGrade([f_lat, l_lat], [f_lon, l_lon])
    distPontos = calcDistPontos(tamGrade, ni, nj)

    lat, lon = f_lat, f_lon
    # PEGA TODOS OS PONTOS DO GRIB
    while lat <= l_lat and lon <= l_lon:
        indices = calcIndices([f_lat, l_lat], [f_lon, l_lon], float(lat), float(lon), distPontos)
        pontosProximos = calcPontosProx(indices, distPontos, [f_lat, l_lat], [f_lon, l_lon])
        distancias = calcDistancia(float(lat), float(lon), pontosProximos, indices)
        menor = acharMenorDistancia(distancias)
        valor = pegarValor(menor['Pos'], arquivo, grib_position)

        data.append({'latitude': menor['Lat'], 'longitute': menor['Lon'], 'valor': valor})

        if lat < l_lat:
            lat += i_increment
        elif lat == l_lat:
            lon += j_increment
            lat = f_lat
    #############################################
    return data


def read_cmdline():
    '''
        python read.py -g grib_file.bufr -p 1 -o data.json
    '''
    p = argparse.ArgumentParser()
    p.add_argument('-g', '--grib', help='GRIB que será lido')
    p.add_argument('-p', '--position', help='Posicao do GRIB no arquivo')
    p.add_argument('-o', '--output', help='Nome do arquivo de saida')
    args = p.parse_args()
    return args


def main():
    inicio_execucao = time.time()
    cmdLine = read_cmdline() # Ler parâmetros de entrada
    valores = pegarValores(cmdLine.grib, cmdLine.position)
    with open(cmdLine.output, 'w') as outfile:  
        json.dump(valores, outfile)
    fim_execucao = time.time()
    tempo = int(fim_execucao - inicio_execucao)
    minutos, segundos = tempo // 60, tempo % 60
    print 'Tempo de Execução - ' + str(minutos).zfill(2) + ':' + str(segundos).zfill(2)


if __name__ == '__main__':
    main()
